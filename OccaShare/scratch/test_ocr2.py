import cv2
import numpy as np
import pytesseract
import re
from typing import Dict, Any, List, Tuple
from pytesseract import Output

class OCRPipeline:
    def __init__(self):
        pass

    def _deskew(self, image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.bitwise_not(gray)
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        coords = np.column_stack(np.where(thresh > 0))
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45: angle = -(90 + angle)
        else: angle = -angle
        if abs(angle) < 0.5 or abs(angle - 90) < 0.5 or abs(angle + 90) < 0.5:
            return image
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    def _auto_crop(self, image: np.ndarray) -> np.ndarray:
        """Find largest contour assuming it's the ID card and crop it."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 30, 150)
        contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours: return image
        c = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(c)
        # Only crop if contour is reasonably large
        if w > image.shape[1] * 0.5 and h > image.shape[0] * 0.5:
            return image[y:y+h, x:x+w]
        return image

    def _preprocess(self, image: np.ndarray, aggressive=False) -> np.ndarray:
        image = self._deskew(image)
        image = self._auto_crop(image)

        height, width = image.shape[:2]
        scaling_factor = 3.0 if aggressive else (2.0 if height < 800 else 1.0)
        upscaled = cv2.resize(image, (int(width * scaling_factor), int(height * scaling_factor)), interpolation=cv2.INTER_CUBIC)

        gray = cv2.cvtColor(upscaled, cv2.COLOR_BGR2GRAY)

        # Brightness normalization
        gray = cv2.normalize(gray, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)

        # Edge enhancement / Sharpen
        kernel_sharpen = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        sharpened = cv2.filter2D(gray, -1, kernel_sharpen)

        # Background subtraction
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 21))
        bg = cv2.morphologyEx(sharpened, cv2.MORPH_DILATE, kernel)
        gray_sub = cv2.divide(sharpened, bg, scale=255)

        # Denoise
        filtered = cv2.bilateralFilter(gray_sub, 9, 75, 75)

        # Adaptive Threshold
        if aggressive:
            thresh = cv2.adaptiveThreshold(filtered, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 3)
        else:
            thresh = cv2.adaptiveThreshold(filtered, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        
        return thresh

    def extract_with_confidence(self, image: np.ndarray, psm_modes=[6, 11, 4]) -> Tuple[str, List[Dict]]:
        best_text = ""
        best_data = []

        for psm in psm_modes:
            config = f'--oem 3 --psm {psm} -l eng'
            try:
                data = pytesseract.image_to_data(image, config=config, output_type=Output.DICT)
                text_parts = []
                word_data = []
                for i in range(len(data['text'])):
                    word = data['text'][i].strip()
                    if word:
                        conf = int(data['conf'][i])
                        text_parts.append(word)
                        word_data.append({"word": word, "conf": conf})
                
                current_text = " ".join(text_parts)
                if len(current_text) > len(best_text):
                    best_text = current_text
                    best_data = word_data
                
                if len(current_text) > 100:  # Sufficient text found
                    break
            except Exception as e:
                print(f"OCR Error with PSM {psm}: {e}")
                
        return best_text, best_data

    def calculate_field_confidence(self, field_value: str, word_data: List[Dict]) -> str:
        """Matches extracted field value to OCR word data to get avg confidence. 
           Returns 'LOW CONFIDENCE' if avg < 50, else the field_value.
           If field_value is empty, returns 'NOT DETECTED'."""
        if not field_value or not str(field_value).strip():
            return "NOT DETECTED"
            
        words = str(field_value).split()
        total_conf = 0
        match_count = 0
        
        # Simple lookup: O(N*M) but N and M are small
        for w in words:
            # find w in word_data
            for d in word_data:
                if w.lower() in d['word'].lower() or d['word'].lower() in w.lower():
                    total_conf += d['conf']
                    match_count += 1
                    break # count once
                    
        avg_conf = (total_conf / match_count) if match_count > 0 else 100
        
        if avg_conf < 50:
            return "LOW CONFIDENCE"
        return str(field_value).strip()

    def run_ocr_pipeline(self, image: np.ndarray, id_type: str) -> Dict[str, Any]:
        # Pass 1: Standard preprocessing
        thresh = self._preprocess(image, aggressive=False)
        text, word_data = self.extract_with_confidence(thresh, [6])
        
        # Check if text is sparse
        if len(text.strip()) < 30:
            print("Retrying with aggressive preprocessing and fallback PSMs...")
            thresh_agg = self._preprocess(image, aggressive=True)
            text, word_data = self.extract_with_confidence(thresh_agg, [11, 4])
            
        print("Raw text:", text)
        return self._parse_fields(text, word_data, id_type)

    def _parse_fields(self, text: str, word_data: List[Dict], id_type: str) -> Dict[str, Any]:
        clean = text.upper()
        clean = re.sub(r'[^A-Z0-9\s/.,:-]', '', clean)
        
        # Helper to get line after a keyword
        def get_after(keywords, lines_list, max_lines=2):
            for i, line in enumerate(lines_list):
                if any(kw in line for kw in keywords):
                    # Check same line first
                    for kw in keywords:
                        if kw in line:
                            rest = line.split(kw, 1)[1].strip()
                            if len(rest) > 2 and not re.match(r'^[A-Z\s]+$', rest) is False: 
                                return rest
                    # Check next lines
                    for j in range(1, max_lines + 1):
                        if i + j < len(lines_list):
                            val = lines_list[i+j].strip()
                            if len(val) > 2 and not any(kw in val for kw in ["DATE", "SEX", "WEIGHT", "ADDRESS"]):
                                return val
            return ""

        # Helper for regex matching
        def get_match(pattern, text_corpus, group=1):
            m = re.search(pattern, text_corpus)
            return m.group(group) if m else ""

        lines = [l.strip() for l in clean.split('\n') if l.strip()]
        
        result = {"id_type": id_type}
        
        if id_type == "PhilID (National ID)":
            raw_id = get_match(r'(\d{4}-\d{4}-\d{4}-\d{4})', clean)
            raw_last = get_after(["APELYIDO", "SURNAME"], lines)
            raw_given = get_after(["MGA PANGALAN", "GIVEN NAMES"], lines)
            raw_mid = get_after(["GITNANG APELYIDO", "MIDDLE NAME"], lines)
            raw_dob = get_match(r'((?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z]*\s+\d{1,2},?\s+\d{4})', clean)
            raw_addr = get_after(["ADDRESS", "TIRAHAN"], lines, 3)
            
            result["id_number"] = self.calculate_field_confidence(raw_id, word_data)
            result["last_name"] = self.calculate_field_confidence(raw_last, word_data)
            result["given_names"] = self.calculate_field_confidence(raw_given, word_data)
            result["middle_name"] = self.calculate_field_confidence(raw_mid, word_data)
            result["date_of_birth"] = self.calculate_field_confidence(raw_dob, word_data)
            result["address"] = self.calculate_field_confidence(raw_addr, word_data)

        elif id_type == "Driver's License":
            raw_last = get_after(["LAST NAME"], lines)
            raw_first = get_after(["FIRST NAME"], lines)
            raw_mid = get_after(["MIDDLE NAME"], lines)
            raw_lic = get_match(r'([A-Z]\d{2}-\d{2}-\d{6})', clean)
            raw_nat = get_match(r'NATIONALITY[:\s]*([A-Z]+)', clean)
            raw_sex = get_match(r'\b(M|F|MALE|FEMALE)\b', clean)
            raw_dob = get_match(r'(\d{4}[-/]\d{2}[-/]\d{2})', clean)
            raw_wt = get_match(r'WEIGHT[:\s]*(\d+\s*KG)', clean)
            raw_ht = get_match(r'HEIGHT[:\s]*(\d+\.?\d*\s*M)', clean)
            raw_addr = get_after(["ADDRESS"], lines, 2)
            raw_exp = get_match(r'EXPIRATION DATE[:\s]*(\d{4}[-/]\d{2}[-/]\d{2})', clean)
            raw_agc = get_match(r'AGENCY CODE[:\s]*([A-Z0-9]+)', clean)
            raw_bld = get_match(r'BLOOD TYPE[:\s]*([A-Z][+-])', clean)
            raw_eye = get_match(r'EYES COLOR[:\s]*([A-Z]+)', clean)
            raw_rest = get_match(r'RESTRICTIONS[:\s]*([1-9]+)', clean)
            raw_cond = get_match(r'CONDITIONS[:\s]*([A-Z0-9]+)', clean)

            result.update({
                "last_name": self.calculate_field_confidence(raw_last, word_data),
                "first_name": self.calculate_field_confidence(raw_first, word_data),
                "middle_name": self.calculate_field_confidence(raw_mid, word_data),
                "license_number": self.calculate_field_confidence(raw_lic, word_data),
                "nationality": self.calculate_field_confidence(raw_nat, word_data),
                "sex": self.calculate_field_confidence(raw_sex, word_data),
                "date_of_birth": self.calculate_field_confidence(raw_dob, word_data),
                "weight": self.calculate_field_confidence(raw_wt, word_data),
                "height": self.calculate_field_confidence(raw_ht, word_data),
                "address": self.calculate_field_confidence(raw_addr, word_data),
                "expiration_date": self.calculate_field_confidence(raw_exp, word_data),
                "agency_code": self.calculate_field_confidence(raw_agc, word_data),
                "blood_type": self.calculate_field_confidence(raw_bld, word_data),
                "eyes_color": self.calculate_field_confidence(raw_eye, word_data),
                "restrictions": self.calculate_field_confidence(raw_rest, word_data),
                "conditions": self.calculate_field_confidence(raw_cond, word_data),
            })

        elif id_type == "Passport":
            raw_type = get_match(r'TYPE[:\s]*([A-Z])', clean)
            raw_cc = get_match(r'COUNTRY CODE[:\s]*([A-Z]{3})', clean)
            raw_pass = get_match(r'PASSPORT NO\.?[:\s]*([A-Z0-9]{7,9})', clean)
            raw_last = get_after(["SURNAME", "LAST NAME"], lines)
            raw_given = get_after(["GIVEN NAMES", "FIRST NAME"], lines)
            raw_mid = get_after(["MIDDLE NAME"], lines)
            raw_dob = get_match(r'DATE OF BIRTH[:\s]*(\d{2}\s+[A-Z]{3}\s+\d{4})', clean)
            raw_nat = get_match(r'NATIONALITY[:\s]*([A-Z]+)', clean)
            raw_sex = get_match(r'SEX[:\s]*(M|F|MALE|FEMALE)', clean)
            raw_pob = get_after(["PLACE OF BIRTH"], lines)
            raw_doi = get_match(r'DATE OF ISSUE[:\s]*(\d{2}\s+[A-Z]{3}\s+\d{4})', clean)
            raw_vu = get_match(r'VISA UNTIL[:\s]*(\d{2}\s+[A-Z]{3}\s+\d{4})', clean)
            raw_auth = get_after(["ISSUING AUTHORITY"], lines)
            
            result.update({
                "type": self.calculate_field_confidence(raw_type, word_data),
                "country_code": self.calculate_field_confidence(raw_cc, word_data),
                "passport_number": self.calculate_field_confidence(raw_pass, word_data),
                "last_name": self.calculate_field_confidence(raw_last, word_data),
                "given_names": self.calculate_field_confidence(raw_given, word_data),
                "middle_name": self.calculate_field_confidence(raw_mid, word_data),
                "date_of_birth": self.calculate_field_confidence(raw_dob, word_data),
                "nationality": self.calculate_field_confidence(raw_nat, word_data),
                "sex": self.calculate_field_confidence(raw_sex, word_data),
                "place_of_birth": self.calculate_field_confidence(raw_pob, word_data),
                "date_of_issue": self.calculate_field_confidence(raw_doi, word_data),
                "visa_until": self.calculate_field_confidence(raw_vu, word_data),
                "issuing_authority": self.calculate_field_confidence(raw_auth, word_data)
            })
            
        else:
            # Fallback
            result["full_name"] = self.calculate_field_confidence(get_after(["NAME"], lines), word_data)
            
        # Check if all fields are NOT DETECTED
        all_not_detected = True
        for k, v in result.items():
            if k != "id_type" and v not in ["NOT DETECTED", "LOW CONFIDENCE"]:
                all_not_detected = False
                break
        
        result["_all_not_detected"] = all_not_detected
        return result
