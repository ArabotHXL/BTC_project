# HashInsight Enterprise User Manual

> **Version**: v2.0  
> **Last Updated**: January 2026  
> **Target Audience**: Mining Farm Operators, Hosting Clients, Platform Administrators

---

## Table of Contents

1. [Overview](#1-overview)
2. [Quick Start](#2-quick-start)
3. [User Roles](#3-user-roles)
4. [Feature Modules](#4-feature-modules)
   - 4.1 [Authentication](#41-authentication)
   - 4.2 [CRM Customer Management](#42-crm-customer-management)
   - 4.3 [Hosting Services Management](#43-hosting-services-management)
   - 4.4 [Revenue Calculator](#44-revenue-calculator)
   - 4.5 [AI Intelligent Diagnosis](#45-ai-intelligent-diagnosis)
   - 4.6 [Curtailment Management](#46-curtailment-management)
   - 4.7 [Multilingual Support](#47-multilingual-support)
5. [UI Layout Description](#5-ui-layout-description)
6. [Common Workflows](#6-common-workflows)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Overview

### What is HashInsight Enterprise

HashInsight Enterprise is an enterprise-grade intelligent hosting management platform designed specifically for large-scale Bitcoin mining farms (20MW+). The platform integrates real-time monitoring, AI-powered diagnostics, revenue calculation, CRM customer management, curtailment scheduling, and other core features to help mining farm operators and hosting clients achieve transparent, efficient, and intelligent operational management.

### Target Users

| User Type | Description |
|-----------|-------------|
| **Mining Site Owner** | Enterprises or individuals who own or operate large mining farms (20MW+), responsible for site management, customer service, and curtailment scheduling |
| **Hosting Client** | Customers who host their miners at the mining farm, needing to monitor their miners' operating status and revenue |
| **Platform Administrator** | Responsible for overall platform management, user permission allocation, and system configuration |

### Core Advantages

- **Transparent Operations**: Real-time miner data, revenue reports, curtailment notifications - complete transparency throughout
- **Intelligent Diagnostics**: AI-driven alert diagnostics for rapid root cause identification
- **Efficient Management**: CRM system, ticket system, automated scheduling to improve operational efficiency
- **Data Security**: Enterprise-grade encryption, role-based access control, audit logs
- **Multilingual**: Supports Chinese and English interface switching

### Feature Overview

| Feature Module | Description |
|----------------|-------------|
| 📊 **Hosting Dashboard** | Site overview, miner status, alert monitoring |
| ⚙️ **Miner Management** | Miner list, detail view, batch operations |
| 🤖 **AI Diagnostics** | Intelligent alert analysis, root cause inference, ticket generation |
| ⚡ **Curtailment Management** | Curtailment planning, manual operations, AI optimization suggestions |
| 💰 **Revenue Calculator** | Single miner calculation, batch calculation, ROI analysis |
| 👥 **CRM System** | Customer management, lead tracking, deal management |
| 🎫 **Ticket System** | Issue submission, progress tracking, ticket processing |
| 📈 **Report Analysis** | Revenue reports, operational reports, data export |

---

## 2. Quick Start

### System Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| **Browser** | Chrome 80+, Firefox 75+, Safari 13+ | Chrome Latest Version |
| **Network** | Stable Internet Connection | 10Mbps+ |
| **Resolution** | 1280 x 720 | 1920 x 1080 |
| **JavaScript** | Must be enabled | Must be enabled |

### How to Access the System

1. Open your browser
2. Enter the platform URL in the address bar
3. Navigate to the login page

```
Access URL: https://calc.hashinsight.net
Login Page: /login
```

### First Login Steps

1. **Access the Login Page**
   - Enter the platform URL in your browser's address bar
   - The system will automatically redirect to the login page `/login`

2. **Enter Login Information**
   - Fill in your registered email in the "Email" input field
   - Fill in your password in the "Password" input field

3. **Click Login**
   - Click the "Login" button
   - Wait for system verification

4. **After Successful Login**
   - The system will automatically redirect based on your role
   - Platform Administrator → Site Management page
   - Mining Site Owner → My Customers page
   - Hosting Client → Client Dashboard

> 💡 **Tip**: After your first login, it is recommended to change your initial password immediately to ensure account security.

---

## 3. User Roles

HashInsight Enterprise uses a Role-Based Access Control (RBAC) system where different roles have different functional permissions.

### Role Comparison Table

| Feature | Platform Admin (admin/owner) | Mining Site Owner (mining_site_owner) | Hosting Client (client) |
|---------|:----------------------------:|:-------------------------------------:|:-----------------------:|
| Site Management | ✅ All Sites | ✅ Owned Sites | ❌ |
| Miner Management | ✅ All Miners | ✅ Miners at Owned Sites | 👁 View Own Miners Only |
| Customer Management | ✅ All Customers | ✅ Self-Created Customers | ❌ |
| User Account Management | ✅ | ✅ Create Accounts for Clients | ❌ |
| Curtailment Management | ✅ | ✅ | 👁 View Only |
| Ticket System | ✅ Process All Tickets | ✅ Process Site Tickets | ✅ Submit and View Own Tickets |
| Revenue Calculator | ✅ | ✅ | ✅ |
| Report Export | ✅ | ✅ | ✅ Own Data |
| CRM System | ✅ | ✅ | ❌ |
| AI Diagnostics | ✅ | ✅ | ❌ |

### Platform Administrator

**Role Identifier**: `admin` / `owner`

**Responsibilities**:
- Overall platform management and configuration
- Create and manage mining site owner accounts
- Assign sites to operators
- View global data and reports
- System configuration and security management

**Default Redirect After Login**: `/admin/site-owners`

**Core Permissions**:
- Site management (create, edit, delete)
- User management (create, assign permissions)
- Global data viewing
- System configuration

### Mining Site Owner

**Role Identifier**: `mining_site_owner`

**Responsibilities**:
- Manage assigned mining farm sites
- Provide services to hosting clients
- Monitor miner operating status
- Handle alerts and tickets
- Execute curtailment scheduling

**Default Redirect After Login**: `/hosting/host/my-customers`

**Core Permissions**:
- Full management rights for owned sites
- Customer management (create, edit, assign)
- Miner monitoring and operations
- Ticket processing
- Curtailment management
- AI diagnostics features

### Hosting Client

**Role Identifier**: `client`

**Responsibilities**:
- View operating status of hosted miners
- Understand revenue situation
- Submit technical support tickets
- View curtailment notifications

**Default Redirect After Login**: `/hosting/`

**Core Permissions**:
- View own miner list and status
- View revenue reports
- Submit and track tickets
- Use revenue calculator
- View curtailment plans

---

## 4. Feature Modules

### 4.1 Authentication

#### Login Page

```
Path: /login
```

**Page Elements**:

| Element | Description |
|---------|-------------|
| Email Input | Enter registered email address |
| Password Input | Enter account password |
| Login Button | Submit login request |
| Forgot Password Link | Password reset entry |
| Language Switch | Chinese/English interface toggle |

#### Login Operation Steps

1. **Access Login Page**
   - Enter `/login` in the browser
   - Or click the "Login" button on the homepage

2. **Enter Login Credentials**
   - Email: Fill in your registered email
   - Password: Fill in your account password

3. **Click the "Login" Button**

4. **Automatic Redirect After Successful Login**
   - Redirects to corresponding page based on user role

**Expected Results**:
- Success: Page displays "Login successful! Welcome to BTC Mining Calculator"
- Failure: Page displays "Login failed! You do not have access permission"

#### Forgot Password

1. Click the "Forgot Password" link on the login page
2. Enter your registered email address
3. Click "Send Reset Link"
4. Check your email and click the reset link
5. Set a new password
6. Log in again with the new password

---

### 4.2 CRM Customer Management

The CRM module is used to manage customer relationships, sales leads, and deals.

#### CRM Dashboard

```
Path: /crm/
Path: /crm/dashboard
```

**Dashboard Content**:
- Total customer count statistics
- Active deal count
- Completed deal count
- Data visualization charts

#### Customer List

```
Path: /crm/customers
```

**Page Features**:
- View all customer list
- Search and filter customers
- View customer details
- Create new customers

**Customer List Fields**:

| Field | Description |
|-------|-------------|
| Customer Name | Customer name or company name |
| Email | Contact email |
| Phone | Contact phone number |
| Company | Company affiliation |
| Status | Customer status (lead/active/inactive) |
| Created At | Customer record creation time |

#### Create New Customer

**Operation Steps**:

1. Navigate to `/crm/customers`
2. Click the "New Customer" button
3. Fill in the customer information form:
   - Customer Name (required)
   - Email (required)
   - Phone
   - Company Name
4. Click the "Save" button
5. **Expected Result**: System displays "Customer created successfully" and the new customer appears in the list

#### Lead Management

```
Path: /crm/leads
```

**Lead Management Features**:
- View sales lead list
- Track lead status
- Convert leads to customers
- Record follow-up activities

#### Deal Management

```
Path: /crm/deals
```

**Deal Management Features**:
- View deal pipeline
- Create new deals
- Update deal stages
- Forecast closing probability

**Deal Stages**:

| Stage | Description |
|-------|-------------|
| Initial Contact | Just started communication |
| Needs Confirmation | Understanding customer requirements |
| Proposal & Quote | Providing solutions |
| Negotiation | Price and terms negotiation |
| Closed Won | Deal completed |
| Closed Lost | Deal failed |

---

### 4.3 Hosting Services Management

#### Host Dashboard

```
Path: /hosting/host/dashboard
Path: /hosting/host
```

**Dashboard Content**:

| Statistics Card | Description |
|-----------------|-------------|
| Total Sites | Number of managed mining farm sites |
| Online Sites | Number of normally operating sites |
| Total Miners | Total miners across all sites |
| Active Miners | Number of normally running miners |
| Capacity Utilization | Power capacity usage ratio |
| Pending Tickets | Number of unresolved tickets |

#### Miner List

```
Path: /hosting/host/devices
Path: /hosting/host/miners
```

**Miner List Fields**:

| Field | Description |
|-------|-------------|
| Miner ID | Unique identifier |
| Model | Miner model (e.g., Antminer S19) |
| Status | Operating status (active/inactive/maintenance) |
| Real-time Hashrate | Current hashrate (TH/s) |
| Power Consumption | Current power consumption (W) |
| Temperature | Maximum temperature (°C) |
| Site | Site where the miner is located |
| Customer | Customer who owns the miner |
| Last Updated | Time of last data update |

**Miner Status Icons**:

| Status | Icon | Description |
|--------|------|-------------|
| 🟢 Online | Green | Running normally |
| 🔴 Offline | Red | Stopped running |
| 🟡 Alert | Yellow | Running abnormally |
| ⚪ Curtailed | Gray | Paused due to curtailment |

#### Event Monitoring

```
Path: /hosting/host/event_monitoring
Path: /hosting/host/event-monitoring
```

**Features**:
- Real-time alert list
- Alert severity classification
- AI intelligent diagnosis entry
- Alert acknowledgment and processing

**Alert Severity Levels**:

| Level | Color | Description |
|-------|-------|-------------|
| Critical | Red | Serious issue, requires immediate attention |
| Warning | Yellow | Warning, needs attention |
| Info | Blue | Informational notification |

#### Ticket Management

```
Path: /hosting/host/tickets
```

**Ticket Fields**:

| Field | Description |
|-------|-------------|
| Ticket Number | Unique identifier |
| Title | Brief description of the issue |
| Type | Issue category |
| Priority | Urgency level |
| Status | Processing status |
| Submitter | Ticket creator |
| Created At | Submission time |

**Ticket Status**:

| Status | Description |
|--------|-------------|
| open | New, pending processing |
| assigned | Handler assigned |
| in_progress | Processing in progress |
| resolved | Resolved |
| closed | Closed |

#### My Customers

```
Path: /hosting/host/my-customers
```

**Features**:
- View customers assigned to your sites
- Assign customers to sites
- Create login accounts for customers
- Edit customer information

**Operation Steps - Assign Customer to Site**:

1. Navigate to `/hosting/host/my-customers`
2. Click the "Assign Customer" button
3. In the popup window:
   - Select the customer to assign (from CRM customer list)
   - Select the target site
4. Click "Confirm Assignment"
5. **Expected Result**: Customer appears in the My Customers list

**Operation Steps - Create Login Account for Customer**:

1. Find the target customer in the customer list
2. Click the "Create Account" button on that row
3. System automatically generates a temporary password
4. Provide login credentials to the customer
5. **Expected Result**: Customer can log into the system with the new account

---

### 4.4 Revenue Calculator

#### Single Miner Calculator

```
Path: /calculator
```

**Input Parameters**:

| Parameter | Description | Unit | Example Value |
|-----------|-------------|------|---------------|
| Miner Model | Select miner model | - | Antminer S19 Pro |
| Hashrate | Miner hashrate | TH/s | 110 |
| Power Consumption | Miner power consumption | W | 3250 |
| Electricity Cost | Power cost | $/kWh | 0.05 |

**Output Results**:

| Metric | Description |
|--------|-------------|
| Daily Revenue (BTC) | Daily mining BTC revenue |
| Daily Revenue (USD) | Daily mining USD revenue |
| Daily Electricity Cost | Daily power cost |
| Daily Net Profit | Daily revenue minus daily electricity cost |
| Monthly Net Profit | Monthly net profit |
| Yearly Net Profit | Yearly net profit |
| Payback Period | Estimated investment recovery time |

**Operation Steps**:

1. Navigate to `/calculator`
2. Select miner model from the dropdown menu
3. System auto-fills hashrate and power consumption (can be manually modified)
4. Enter electricity cost
5. Click the "Calculate" button
6. **Expected Result**: Page displays detailed revenue calculation results

#### Batch Calculator

```
Path: /batch-calculator
```

**Features**:
- Calculate revenue for multiple miners simultaneously
- Support CSV file import
- Summary statistics and comparative analysis
- Result export

**Batch Calculation Operation Steps**:

1. Navigate to `/batch-calculator`
2. Download the CSV template file
3. Fill in miner data in the template
4. Upload the completed CSV file
5. Click the "Batch Calculate" button
6. **Expected Result**: Displays revenue for each miner and summary statistics

**Understanding Calculation Results**:

| Metric | Calculation Formula |
|--------|---------------------|
| Daily Revenue | (Hashrate / Network Hashrate) × Daily Block Reward × BTC Price |
| Daily Electricity Cost | Power(kW) × 24 hours × Electricity Rate |
| Daily Net Profit | Daily Revenue - Daily Electricity Cost |
| Payback Period | Miner Price / Daily Net Profit |

---

### 4.5 AI Intelligent Diagnosis

#### Alert Diagnosis Feature

**Entry Points**:
- Event Monitoring page `/hosting/host/event_monitoring`
- "AI Diagnose" button on alert cards

**Diagnosis Process**:

1. View the alert list on the Event Monitoring page
2. Find the alert that needs diagnosis
3. Click the "AI Diagnose" button on the alert card
4. Wait for AI analysis (approximately 3-5 seconds)
5. View diagnosis results

**Diagnosis Result Content**:

AI diagnosis generates **Top 3 Root Cause Hypotheses**, each containing:

| Content | Description |
|---------|-------------|
| Hypothesis Description | Possible cause of the problem |
| Confidence Level | AI's confidence percentage in the hypothesis |
| Evidence | Data supporting the hypothesis |
| Recommended Action | Suggested verification or fix steps |
| Risk Level | Problem severity assessment |

**Diagnosis Example**:

```
📋 Alert Type: Hashrate Drop
🎯 Most Likely Cause: Mining Pool Connection Abnormality (Confidence 75%)

Evidence:
- Pool Latency: 320ms (Threshold: 200ms)
- Reject Rate: 3.2% (Threshold: 2%)

Recommended Actions:
1. Check network connection status
2. Try switching to backup mining pool
3. Restart miner network module
```

#### Ticket Draft Generation

After AI diagnosis is complete, you can generate a ticket with one click:

1. View AI diagnosis results
2. Click the "Generate Ticket" button
3. AI automatically fills in ticket content:
   - Problem description
   - Diagnosis results
   - Recommended resolution plan
4. Confirm or edit ticket content
5. Click "Submit Ticket"

---

### 4.6 Curtailment Management

#### Curtailment Plan List

```
Path: /hosting/host/curtailment
```

**Page Content**:

| Element | Description |
|---------|-------------|
| Curtailment Plan List | All scheduled curtailment arrangements |
| Plan Status | Pending/Executing/Completed/Cancelled |
| Create Curtailment Button | Add new curtailment plan |
| AI Suggestion Entry | Get intelligent curtailment suggestions |

**Curtailment Plan Fields**:

| Field | Description |
|-------|-------------|
| Plan Name | Curtailment plan identifier |
| Start Time | Planned execution start time |
| End Time | Planned end time |
| Curtailment Ratio | Power reduction percentage |
| Affected Miners | Number of affected miners |
| Status | Plan execution status |
| Execution Mode | Automatic/Manual |

#### Create Curtailment Plan

**Operation Steps**:

1. Navigate to `/hosting/host/curtailment`
2. Click the "Create Curtailment Plan" button
3. Fill in plan information:
   - Plan Name
   - Start Time
   - End Time
   - Curtailment Ratio (%)
   - Select affected sites/miners
   - Select execution mode
4. Click "Confirm Create"
5. **Expected Result**: New plan appears in the list with status "Pending"

#### Manual Curtailment Operation

**Emergency Curtailment Steps**:

1. Click "Manual Curtailment" on the curtailment management page
2. Select target sites or miners
3. Set curtailment ratio
4. Click "Execute Now"
5. Confirm operation
6. **Expected Result**: Selected miners begin reduced power operation

#### AI Curtailment Suggestions

**Steps to Get AI Suggestions**:

1. Click the "AI Curtailment Suggestion" button
2. AI analyzes current situation:
   - Electricity price forecast
   - Bitcoin price
   - Miner efficiency ranking
   - Network difficulty
3. View suggestion results:
   - Recommended curtailment time periods
   - Recommended miners to curtail
   - Estimated cost savings
   - Estimated revenue impact
4. Choose to accept or reject suggestions

---

### 4.7 Multilingual Support

#### Language Switch Location

The language switch button is located in the **top right navigation bar**.

#### Supported Languages

| Language | Identifier | Description |
|----------|------------|-------------|
| Chinese | 中文 / ZH | Simplified Chinese interface |
| English | EN | English interface |

#### Language Switch Operation

1. Find the language switch button in the top right corner
2. Click the button to toggle between "中文" and "English"
3. Page automatically refreshes to the selected language
4. Language preference is automatically saved

> 💡 **Tip**: Language settings are saved in the browser and automatically applied on next visit.

---

## 5. UI Layout Description

### General Layout Structure

```
┌─────────────────────────────────────────────────────┐
│                    Top Navigation Bar               │
│  [Logo]  [Navigation Menu]      [Language] [User]   │
├─────────────────────────────────────────────────────┤
│        │                                            │
│        │                                            │
│ Sidebar│              Main Content Area             │
│  Menu  │                                            │
│        │                                            │
│        │                                            │
├─────────────────────────────────────────────────────┤
│                        Footer                       │
└─────────────────────────────────────────────────────┘
```

### Hosting Dashboard Layout

**Top Navigation Bar**:
- Logo (click to return to homepage)
- Main Menu: Dashboard | Sites | Miners | Curtailment | Tickets
- Language Switch: 中文/EN
- User Menu: Settings | Logout

**Main Content Area**:
- Statistics card area (4-6 KPI cards)
- Chart area (hashrate trends, power distribution)
- Recent alerts list
- Pending items

**Key Buttons**:
- "Create Site" - Add new mining farm
- "Refresh Data" - Update real-time data
- "Export Report" - Download data report

### Miner List Page Layout

**Toolbar**:
- Search box
- Filters (site, status, model, customer)
- Batch operation buttons
- Export button

**Data Table**:

| Column | Width | Description |
|--------|-------|-------------|
| ☐ | 40px | Checkbox |
| ID | 100px | Miner ID |
| Model | 150px | Miner model |
| Status | 80px | Status icon |
| Hashrate | 100px | Real-time hashrate |
| Power | 100px | Current power consumption |
| Temperature | 80px | Maximum temperature |
| Site | 120px | Site location |
| Customer | 120px | Customer owner |
| Actions | 150px | View/Edit/Diagnose |

**Pagination Controls**:
- Items per page: 25 | 50 | 100
- Page navigation: « 1 2 3 ... 10 »
- Total record count display

### Calculator Page Layout

**Left Side - Input Area**:
- Miner model dropdown selection
- Hashrate input field (TH/s)
- Power consumption input field (W)
- Electricity cost input field ($/kWh)
- Miner price input field (optional)
- "Calculate" button

**Right Side - Results Area**:
- Real-time BTC price display
- Network difficulty display
- Revenue calculation result cards
  - Daily/Monthly/Yearly revenue
  - Electricity cost
  - Net profit
  - Payback period
- Revenue trend chart

---

## 6. Common Workflows

### Workflow 1: Create and Manage Customers

**Complete Operation Flow**:

1. **Create Customer in CRM**
   - Navigate to `/crm/customers`
   - Click "New Customer"
   - Fill in customer information (name, email, phone, company)
   - Click "Save"

2. **Assign Customer to Site**
   - Navigate to `/hosting/host/my-customers`
   - Click "Assign Customer"
   - Select the newly created customer
   - Select target site
   - Click "Confirm"

3. **Create Login Account for Customer**
   - Find the customer in the customer list
   - Click "Create Account"
   - Record the system-generated temporary password
   - Send login information to the customer

4. **Verification**
   - Customer logs in with new account
   - Confirm they can view their own miners

### Workflow 2: Monitor Miner Health Status

**Daily Monitoring Flow**:

1. **Log into System**
   - Log in with mining site owner account

2. **View Dashboard**
   - Navigate to `/hosting/host/dashboard`
   - Check key metrics:
     - Online miner ratio
     - Active alert count
     - Pending tickets

3. **Check Alerts**
   - Navigate to `/hosting/host/event_monitoring`
   - View alert list
   - Sort by severity

4. **Handle Anomalies**
   - For Critical alerts, immediately use AI diagnosis
   - For Warning alerts, log and schedule handling
   - For Info notifications, just take note

5. **View Miner Details**
   - Click miner link in alert
   - View detailed operating data
   - View historical trend charts

### Workflow 3: Use AI Diagnosis to Respond to Alerts

**AI Diagnosis Operation Flow**:

1. **Discover Alert**
   - See new alert on Event Monitoring page
   - Alert types: Miner Offline / Hashrate Drop / High Temperature

2. **Start AI Diagnosis**
   - Click the "AI Diagnose" button on the alert card
   - Wait for analysis to complete (3-5 seconds)

3. **View Diagnosis Results**
   - Read Top 3 Root Cause Hypotheses
   - Check confidence level of each hypothesis
   - Understand evidence data

4. **Execute Recommended Actions**
   - Verify according to recommended actions
   - Generate ticket if on-site handling is needed

5. **Create Ticket**
   - Click "Generate Ticket"
   - Confirm AI-generated ticket content
   - Add necessary information
   - Submit ticket

6. **Track Processing**
   - Track processing progress in ticket system
   - Close ticket after confirming issue is resolved

### Workflow 4: Calculate Mining Revenue

**Revenue Calculation Flow**:

1. **Choose Calculation Method**
   - Single miner calculation: `/calculator`
   - Batch calculation: `/batch-calculator`

2. **Enter Parameters** (Single Miner Calculation)
   - Select miner model
   - Confirm hashrate and power consumption data
   - Enter electricity rate

3. **View Results**
   - Daily/Monthly/Yearly revenue forecast
   - Electricity cost estimate
   - Net profit calculation
   - Payback period forecast

4. **Batch Calculation** (Optional)
   - Download CSV template
   - Fill in multiple miner data
   - Upload file
   - View summary results

5. **Export Report**
   - Click "Export" button
   - Select format (PDF/Excel)
   - Download and save

### Workflow 5: Create Technical Support Ticket

**Ticket Submission Flow**:

1. **Enter Ticket System**
   - Navigate to `/hosting/host/tickets` (Operator)
   - Or `/hosting/client/tickets` (Client)

2. **Create New Ticket**
   - Click "New Ticket" button

3. **Fill in Ticket Information**
   - Select ticket type:
     - Hardware Issue
     - Network Issue
     - Software Issue
     - Billing Inquiry
     - Other
   - Fill in title (brief description)
   - Fill in detailed description
   - Select priority
   - Associate related miners (optional)

4. **Submit Ticket**
   - Confirm information is correct
   - Click "Submit" button

5. **Track Progress**
   - View status in ticket list
   - Check replies from operations personnel
   - Add information or reply to comments

6. **Confirm Resolution**
   - Confirm ticket when issue is resolved
   - Ticket status changes to "Resolved"

---

## 7. Troubleshooting

### Common Issues and Solutions

#### Q1: Cannot Log into System

**Possible Causes**:
- Incorrect username or password
- Account is locked
- Account permissions not enabled

**Solutions**:
1. Confirm email address is entered correctly
2. Check password is correct (note case sensitivity)
3. Use "Forgot Password" to reset password
4. If failed multiple times, account may be locked - wait 30 minutes and retry
5. Contact administrator to confirm account status

#### Q2: Page Displays "Access Denied"

**Possible Causes**:
- Current role does not have permission to access this feature
- Session has expired

**Solutions**:
1. Confirm your account role has permission to access this page
2. Try logging in again
3. Contact administrator to confirm permission settings

#### Q3: Miner Data Not Updating

**Possible Causes**:
- Miner is offline
- Collector connection abnormality
- Network latency

**Solutions**:
1. Check miner network connection
2. Check "Last Updated" time on miner management page
3. Contact on-site to check miner status
4. Submit ticket for operations personnel to investigate

#### Q4: AI Diagnosis Returns Error

**Possible Causes**:
- System is busy
- Insufficient data for analysis
- Service temporarily unavailable

**Solutions**:
1. Wait a few seconds and retry
2. Refresh page and try again
3. If continues to fail, submit ticket for feedback

#### Q5: Calculator Results Not Accurate

**Possible Causes**:
- BTC price/difficulty data delayed
- Input parameters are incorrect

**Solutions**:
1. Confirm hashrate and power consumption data are correct
2. Check if BTC price and difficulty displayed on page are current
3. Wait a few minutes for data to update and recalculate

#### Q6: Cannot Create Customer Account

**Possible Causes**:
- Customer email already in use
- Missing required information

**Solutions**:
1. Confirm customer email is not used by another account
2. Confirm all required fields are filled
3. Refresh page and retry

#### Q7: Curtailment Plan Not Executed

**Possible Causes**:
- Plan time settings are incorrect
- Site/miner selection is wrong
- System scheduling delay

**Solutions**:
1. Check if plan start time is correct
2. Confirm selected sites and miners are correct
3. Check if plan status is "Pending"
4. Contact operations personnel to investigate

### Getting Technical Support

If the above methods cannot solve your issue, please contact us through the following channels:

| Contact Method | Details |
|----------------|---------|
| 📧 **Support Email** | support@hashinsight.com |
| 📞 **Service Hotline** | 400-XXX-XXXX (Weekdays 9:00-18:00) |
| 💬 **Online Support** | Chat window in bottom right corner of platform |
| 🎫 **Ticket System** | Submit ticket via "Technical Support" in platform |

**Please provide when submitting an issue**:
- Your account email
- Time when issue occurred
- Detailed description of the issue
- Related miner IDs (if applicable)
- Screenshots or error messages

---

## Appendix

### Glossary

| Term | English | Description |
|------|---------|-------------|
| Hashrate | Hashrate | Computing power of a miner, unit TH/s |
| Power Consumption | Power Consumption | Electricity consumed by miner, unit W or kW |
| Curtailment | Curtailment | Planned reduction of miner operating power |
| Ticket | Ticket | Issue feedback and tracking record |
| RBAC | Role-Based Access Control | Role-based access control |
| Confidence | Confidence | Reliability level of AI diagnosis results |

### Keyboard Shortcuts

| Shortcut | Function |
|----------|----------|
| Ctrl + F | In-page search |
| F5 | Refresh page |
| Esc | Close popup |

### System Route Reference

| Page | Path |
|------|------|
| Login | `/login` |
| Homepage | `/` |
| Calculator | `/calculator` |
| Batch Calculator | `/batch-calculator` |
| CRM Dashboard | `/crm/` |
| Customer List | `/crm/customers` |
| Deal Management | `/crm/deals` |
| Hosting Dashboard | `/hosting/host/dashboard` |
| Miner List | `/hosting/host/devices` |
| Event Monitoring | `/hosting/host/event_monitoring` |
| Curtailment Management | `/hosting/host/curtailment` |
| Ticket Management | `/hosting/host/tickets` |
| My Customers | `/hosting/host/my-customers` |
| Client Dashboard | `/hosting/client/dashboard` |
| Client Miners | `/hosting/client/miners` |
| Client Tickets | `/hosting/client/tickets` |

---

**Thank you for choosing HashInsight Enterprise!**

We are committed to providing you with transparent, efficient, and intelligent mining farm hosting services.

If you have any suggestions or feedback, please feel free to contact us at any time.

---

*© 2026 HashInsight Enterprise. All Rights Reserved.*
