# Complete Admin Journey

Narito ang detalyadong flowchart ng proseso ni Admin, mula login hanggang sa pagtapos ng mga gawain.

```mermaid
flowchart TD
    %% LOGIN PHASE
    Start([Simula: Admin Login Page]) --> Login[Input Email & Password]
    Login --> AuthCheck{Credentials Valid?}
    
    AuthCheck -- "Hindi" --> Error[Show Error: 'Invalid Credentials']
    Error --> Login
    
    AuthCheck -- "Oo" --> Session[Initiate Session & JWT Token]
    Session --> Redirect[Redirect to /admin/dashboard]

    %% DASHBOARD HUB
    Redirect --> Dashboard[Admin Dashboard Hub]
    Dashboard --> NotifCheck[Real-time WebSocket Check for New Alerts]
    
    %% MAIN NAVIGATION DECISION
    Dashboard --> TaskSelect{Anong Gagawin?}

    %% SUBGRAPH: CATERER MANAGEMENT
    subgraph Caterer_Management ["1. Manage Caterers"]
        C1[View Caterer List] --> C2{Action?}
        C2 -- "Verification" --> C3[Review KYC Documents]
        C3 --> C4{Pumasa?}
        C4 -- "Oo" --> C5[Approve: System Activates Account]
        C4 -- "Hindi" --> C6[Reject / Request Revision]
        C2 -- "Status" --> C7[Global Toggle: Active/Suspended]
        C2 -- "Delete" --> C8[Move to Archives]
    end

    %% SUBGRAPH: COMPLIANCE & KYC
    subgraph Compliance_KYC ["2. Compliance (KYC) Queue"]
        K1[Review Unverified Users] --> K2[OCR Match Result Check]
        K2 --> K3{Manual Review Needed?}
        K3 -- "Oo" --> K4[Check Audit Logs & ID Images]
        K4 --> K5[Final Decision: Approve/Reject]
    end

    %% SUBGRAPH: FINANCIALS
    subgraph Finance ["3. Earnings & Payments"]
        F1[View Paid Bookings] --> F2[System Calculates Commission]
        F2 --> F3[Monitor ROI Performance]
    end

    %% SUBGRAPH: SYSTEM MODERATION
    subgraph Moderation ["4. Content & Inquiries"]
        M1[Manage Visitor Inquiries] --> M2[Respond via Email Thread]
        M1 --> M3[Update Status: New/Responded]
        M4[Review Platform Feedback] --> M5[Toggle: Highlight for Marketing]
    end

    %% SUBGRAPH: CONFIGURATION
    subgraph Config ["5. Site Settings & Archives"]
        S1[Update Branding: Logo/Favicon] --> S2[Set Site-wide Commission]
        S2 --> S3[Global Maintenance Mode Toggle]
        S4[Archive Vault] --> S5{Action?}
        S5 -- "Undo" --> S6[Restore Record]
        S5 -- "Clean" --> S7[Permanently Delete]
    end

    %% CONNECTING PATHS
    TaskSelect -- "Caterers" --> Caterer_Management
    TaskSelect -- "Compliance" --> Compliance_KYC
    TaskSelect -- "Earnings" --> Finance
    TaskSelect -- "Support" --> Moderation
    TaskSelect -- "System/Vault" --> Config

    %% TERMINATION
    C5 --> Dashboard
    C6 --> Dashboard
    K5 --> Dashboard
    F3 --> Dashboard
    M3 --> Dashboard
    S3 --> Dashboard
    S7 --> Dashboard

    Dashboard -- "Gawain Tapos" --> Logout([Logout: Delete Cookies & End Session])
```

### Pagsusuri base sa iyong Website:
1.  **Login Logic**: Sa `auth.py`, ang admin ay dadaan sa `verify_password` at ire-redirect sa `/admin/dashboard` kapag successful.
2.  **Caterer Management**: Sa `admin.py`, ang pag-approve ng caterer ay awtomatikong mag-seset ng kanilang status to `active` (ito ang `C5` sa flowchart).
3.  **Real-time Notifications**: Nag-uupdate ang badge kapag may bagong registration o booking via WebSocket.
4.  **Recycle Bin (Archives)**: Pwedeng i-restore o tuluyang burahin ang records gaya ng Archived Bookings at Users.
