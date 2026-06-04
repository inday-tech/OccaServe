import sys
import os
import asyncio

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.verification import verification_service
from tests.test_real_kyc import create_dummy_images

async def main():
    id_filename, _ = create_dummy_images()
    id_path = f"/api/bookings/kyc/view/{id_filename}"
    res = await verification_service.extract_id_data(id_path, "PhilSys / PhilID")
    import pprint
    pprint.pprint(res)

if __name__ == "__main__":
    asyncio.run(main())
