# 🧪 Mock Data for Testing "Add Miner" Feature

This guide explains how to use the mock data generator to test the "+ Add Miner" functionality.

---

## 🚀 Quick Start

### 1. Generate Mock Data

```bash
conda activate snakeenv
python test/create_mock_miner_data.py
```

This will:
- ✅ Generate 10 mock miners with realistic data
- ✅ Save data in multiple formats (JSON, CSV, JavaScript)
- ✅ Display the data in the terminal

---

## 📋 Generated Files

After running the script, you'll get:

1. **`mock_miner_data.json`** - JSON format for API testing
2. **`mock_miner_test.js`** - JavaScript code for browser console testing
3. **`mock_miners_import.csv`** - CSV format for batch import

---

## 🧪 Testing Methods

### Method 1: Browser Console (Easiest)

1. Open the application in your browser: `http://localhost:5001`
2. Log in and navigate to **Hosting → Miner Management**
3. Open browser console (F12 → Console tab)
4. Copy the code from `test/mock_miner_test.js`
5. Paste and run:
   ```javascript
   testAddMiner(0);  // Add first miner
   testAddMiner(1);  // Add second miner
   ```

### Method 2: Manual Form Testing

1. Navigate to **Hosting → Miner Management**
2. Click **"+ Add Miner"** button
3. Fill in the form using data from the generated mock data:

**Required Fields:**
- **Serial Number**: `BM2025000001` (from mock data)
- **Miner Model**: Select from dropdown (e.g., "Antminer S19 Pro")
- **Site**: Select a site from dropdown
- **Customer Email**: Enter customer email

**Optional Fields:**
- **IP Address**: `192.168.1.100` (from mock data)
- **Rack Position**: `A-01-05` (from mock data)
- **Notes**: Any notes you want

4. Click **"Add Miner"**

### Method 3: API Testing (cURL)

```bash
# Get a mock miner data
MINER_DATA='{
  "site_id": 1,
  "customer_id": 1,
  "miner_model_id": 1,
  "serial_number": "BM2025000001",
  "actual_hashrate": 110.0,
  "actual_power": 3250,
  "ip_address": "192.168.1.100",
  "rack_position": "A-01-05",
  "notes": "Test miner"
}'

# Make API call (after logging in and getting session)
curl -X POST http://localhost:5001/hosting/api/miners \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d "$MINER_DATA"
```

### Method 4: Batch Import (CSV)

1. Navigate to **Hosting → Miner Management**
2. Click **"Batch Import"** (if available)
3. Upload the generated `mock_miners_import.csv` file

---

## 📊 Mock Data Structure

Each mock miner includes:

```json
{
  "site_id": 1,                    // Required: Site ID
  "customer_id": 1,               // Required: Customer ID
  "miner_model_id": 1,            // Required: Miner Model ID
  "serial_number": "BM2025000001", // Required: Unique serial number
  "actual_hashrate": 110.0,        // Required: Hashrate in TH/s
  "actual_power": 3250,           // Required: Power in Watts
  "ip_address": "192.168.1.100",  // Optional: IP address
  "rack_position": "A-01-05",      // Optional: Rack position
  "mac_address": "aa:bb:cc:dd:ee:ff", // Optional: MAC address
  "notes": "Test miner"            // Optional: Notes
}
```

---

## 🔧 Customizing Mock Data

### Change Number of Miners

Edit `test/create_mock_miner_data.py`:

```python
mock_data = create_mock_miner_data(count=20)  # Generate 20 miners
```

### Use Specific Site/Customer

```python
mock_data = create_mock_miner_data(
    count=5,
    site_id=2,        # Use site ID 2
    customer_id=3,    # Use customer ID 3
    miner_model_id=1  # Use miner model ID 1
)
```

### Custom Miner Models

The script automatically creates these models if they don't exist:
- Antminer S19 Pro
- Antminer S19j Pro
- WhatsMiner M30S++
- WhatsMiner M31S+
- AvalonMiner 1246

---

## 📝 Example Mock Data

Here's an example of generated mock data:

```
🔧 Miner #1:
  Serial Number: BM2025000001
  Model ID: 1
  Site ID: 1
  Customer ID: 1
  Hashrate: 110.0 TH/s
  Power: 3250 W
  IP Address: 192.168.1.100
  Rack Position: A-01-05
  Notes: Mock test miner #1 - Antminer S19 Pro
```

---

## ⚠️ Important Notes

1. **Database Requirements:**
   - At least one hosting site must exist
   - At least one customer/user must exist
   - Miner models will be auto-created if missing

2. **Serial Number Uniqueness:**
   - Each serial number must be unique
   - If you get "序列号已存在" error, the serial number is already in use

3. **Permissions:**
   - You need to be logged in
   - You need appropriate RBAC permissions for hosting module

4. **Approval Status:**
   - Admin/Owner: Miners are auto-approved
   - Client/Customer: Miners require approval

---

## 🐛 Troubleshooting

### "No hosting sites found"
```bash
# Create a site first through the UI or database
# Navigate to: Hosting → Site Management → Add Site
```

### "No customers found"
```bash
# Create a customer/user account first
# Or use an existing user ID
```

### "序列号已存在" (Serial number exists)
```bash
# The serial number is already in use
# Generate new mock data or use a different serial number
```

### API Returns 401/403
```bash
# Make sure you're logged in
# Check your RBAC permissions for hosting module
```

---

## 📚 Related Files

- `test/create_mock_miner_data.py` - Mock data generator script
- `test/mock_miner_data.json` - Generated JSON data
- `test/mock_miner_test.js` - Browser console test code
- `test/mock_miners_import.csv` - CSV import file

---

## 🎯 Quick Test Checklist

- [ ] Run `python test/create_mock_miner_data.py`
- [ ] Check generated files exist
- [ ] Log in to the application
- [ ] Navigate to Hosting → Miner Management
- [ ] Click "+ Add Miner"
- [ ] Fill form with mock data
- [ ] Submit and verify miner is added
- [ ] Check miner appears in the list

---

Happy Testing! 🚀
