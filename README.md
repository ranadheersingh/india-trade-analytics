# India Trade Analytics: Complete Deliverables Package

**Date**: May 9, 2026  
**Topic**: States Dashboard Fix + Rolling 5-Year Data Window Implementation  
**Status**: Ready to implement

---

## 📋 Contents Overview

This package contains solutions for two separate but related issues:

### Issue 1: States Dashboard Not Loading
Multiple root causes and comprehensive fixes with diagnostics

### Issue 2: Data Filtering Requirement
Implement rolling 5-year window across all queries consistently

---

## 📂 File Directory

### STATES DASHBOARD ISSUES (Fix & Diagnose)

#### 1. **QUICK_ACTION_PLAN.md** (START HERE)
- **Read time**: 5 minutes
- **Purpose**: Quick summary of states dashboard problem and 3-step fix
- **Contains**:
  - Problem statement (30 seconds)
  - Quick 5-minute fix
  - Detailed diagnostics (10-15 min)
  - What to check if still broken
- **Best for**: Getting oriented, understanding the problem

#### 2. **STATES_DASHBOARD_FIX_GUIDE.md** (COMPREHENSIVE)
- **Read time**: 30-45 minutes
- **Purpose**: Complete technical guide with all diagnostic methods
- **Contains**:
  - Root cause analysis (detailed)
  - 7-phase troubleshooting checklist
  - SQL diagnostic queries
  - API testing instructions
  - Expected behavior after fix
  - Rollout plan
  - Common problems & solutions
- **Best for**: Understanding everything, methodical fixing, documentation

#### 3. **STATES_DASHBOARD_ARCHITECTURE.md** (TECHNICAL DEEP-DIVE)
- **Read time**: 20-30 minutes
- **Purpose**: Architectural explanation of why states dashboard works the way it does
- **Contains**:
  - Data architecture (3 sources: DGCIS, COMTRADE, TRADESTAT)
  - Current implementation explanation
  - Complete query flow
  - Testing the fix
  - Recovery checklist
- **Best for**: Understanding the platform design, explaining to others

#### 4. **DATABASE_DIAGNOSTICS.sql**
- **Type**: SQL script (copy/paste into psql)
- **Purpose**: Check actual data state in database
- **Contains**:
  - 12 diagnostic query blocks
  - FY-wise data breakdown
  - TRADESTAT status checks
  - State master data verification
  - Data quality checks
  - Query performance analysis
- **Best for**: Troubleshooting "why is my database empty?"

#### 5. **quick-fix.sh** (Automation)
- **Type**: Bash script
- **Purpose**: Automated 5-minute diagnostics
- **Usage**: `bash quick-fix.sh`
- **Does**:
  - Checks if Docker is running
  - Connects to database
  - Verifies state data exists
  - Tests API endpoint
  - Tests code logic
  - Reports findings clearly
- **Best for**: Fast diagnosis before/after fixes

#### 6. **fix-states-dashboard.sh** (Automation)
- **Type**: Bash script
- **Purpose**: Automated comprehensive fix (15 minutes)
- **Usage**: `bash fix-states-dashboard.sh`
- **Does**:
  - Restarts Docker containers
  - Validates database
  - Tests all endpoints
  - Provides clear next steps
  - Full error reporting
- **Best for**: One-shot fix with validation

---

### ROLLING 5-YEAR WINDOW IMPLEMENTATION (New Feature)

#### 7. **ROLLING_WINDOW_README.md** (START HERE)
- **Read time**: 10 minutes
- **Purpose**: Overview of entire rolling window implementation
- **Contains**:
  - What the requirement is
  - Why it matters (benefits)
  - Quick 30-minute implementation
  - Detailed 1-2 hour implementation
  - Configuration guide
  - Testing examples
  - Troubleshooting
- **Best for**: Understanding the complete package

#### 8. **ROLLING_5_YEAR_IMPLEMENTATION.md** (DETAILED GUIDE)
- **Read time**: 45-60 minutes
- **Purpose**: Comprehensive implementation guide with all details
- **Contains**:
  - Current implementation status (✅/⚠️/❌)
  - Audit of all existing queries
  - Phase 1-3 implementation plan
  - Code changes required
  - Testing strategy
  - Configuration options
  - Migration plan
  - Monitoring & validation
  - Rollback plan
  - Complete checklist
- **Best for**: Thorough implementation, understanding rationale

#### 9. **DASHBOARDS_UPDATE_GUIDE.md** (STEP-BY-STEP)
- **Read time**: 15-20 minutes
- **Purpose**: Exact steps to update dashboards.py
- **Contains**:
  - Step 1: Add import
  - Step 2: Replace function
  - Step 3: Update all calls (with examples)
  - Step 4: Update helper function
  - Complete checklist
  - Testing commands
  - Verification guide
  - Rollback plan
- **Best for**: Implementation time, following along with code

#### 10. **date_utils.py** (IMPLEMENTATION)
- **Type**: Python module (ready to use)
- **Purpose**: Centralized date windowing logic
- **Usage**: Copy to `backend/app/services/date_utils.py`
- **Contains**:
  - `DateWindow` class with all methods
  - `rolling_window()` - get 5-year range
  - `current_fy()` - get current fiscal year
  - `fy_range()` - get fiscal year range
  - Helper methods (formatting, conversion, validation)
  - Full docstrings & examples
  - Extensive logging
- **Best for**: Copy-paste implementation

---

## 🎯 Quick Navigation

### "My states dashboard is blank"
**Follow this path**:
1. ✅ Read: QUICK_ACTION_PLAN.md (5 min)
2. ✅ Run: `bash quick-fix.sh`
3. ✅ Follow instructions in output
4. ❓ Still broken? → Read: STATES_DASHBOARD_FIX_GUIDE.md

### "I want to understand why the dashboard failed"
**Follow this path**:
1. ✅ Read: STATES_DASHBOARD_ARCHITECTURE.md (understanding)
2. ✅ Read: STATES_DASHBOARD_FIX_GUIDE.md (fixes)
3. ✅ Run diagnostic queries from: DATABASE_DIAGNOSTICS.sql

### "I need to implement the 5-year rolling window"
**Follow this path**:
1. ✅ Read: ROLLING_WINDOW_README.md (overview)
2. ✅ Read: ROLLING_5_YEAR_IMPLEMENTATION.md (detailed)
3. ✅ Follow: DASHBOARDS_UPDATE_GUIDE.md (step-by-step)
4. ✅ Copy: date_utils.py to backend/app/services/
5. ✅ Test: Run included test commands

### "I need to fix everything in the next 30 minutes"
**Follow this path**:
1. ✅ Quick fix: `bash quick-fix.sh` (states dashboard)
2. ✅ Quick implement: Copy date_utils.py + follow DASHBOARDS_UPDATE_GUIDE.md Section 2 only
3. ✅ Restart: `docker compose down && docker compose up -d --build`
4. ✅ Verify: Test endpoints

---

## 🔍 File Relationships

```
ISSUE: States Dashboard Not Loading
├─ QUICK_ACTION_PLAN.md (start here - 5 min)
├─ STATES_DASHBOARD_FIX_GUIDE.md (comprehensive - 45 min)
├─ STATES_DASHBOARD_ARCHITECTURE.md (why/how - 30 min)
├─ DATABASE_DIAGNOSTICS.sql (check DB - 10 min)
└─ BASH SCRIPTS
   ├─ quick-fix.sh (diagnose - 5 min)
   └─ fix-states-dashboard.sh (automated fix - 15 min)

FEATURE: Rolling 5-Year Window
├─ ROLLING_WINDOW_README.md (start here - 10 min)
├─ ROLLING_5_YEAR_IMPLEMENTATION.md (detailed - 60 min)
├─ DASHBOARDS_UPDATE_GUIDE.md (step-by-step - 20 min)
└─ date_utils.py (ready-to-use code)
```

---

## 📊 Implementation Matrix

### States Dashboard Fix

| Complexity | Time | Automation | For Who |
|------------|------|-----------|---------|
| Quick diagnosis | 5 min | `quick-fix.sh` | Anyone |
| Automated fix | 15 min | `fix-states-dashboard.sh` | Developers |
| Manual thorough | 45 min | Reference docs | DevOps/Architects |

### Rolling Window Implementation

| Complexity | Time | Difficulty | For Who |
|------------|------|-----------|---------|
| Copy-paste | 30 min | Easy | Junior developers |
| With testing | 1-2 hr | Medium | Mid-level developers |
| With monitoring | 2-3 hr | Medium | DevOps engineers |
| With configuration | 3-4 hr | Medium | architects |

---

## 🧪 Testing Recommendations

### States Dashboard
```bash
# Minimal test (5 min)
bash quick-fix.sh

# Complete test (15 min)
bash fix-states-dashboard.sh

# Manual validation
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8001/api/v1/dashboards/states?fiscal_year=2025" | jq .
```

### Rolling Window
```bash
# Unit test
cd backend && pytest tests/test_date_utils.py -v

# Integration test
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8001/api/v1/dashboards/executive" | jq .yoy_trend

# Verify window size
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8001/api/v1/dashboards/executive" | jq '.yoy_trend | length'
# Should be <= 60
```

---

## 📝 Checklists

### States Dashboard Fix Checklist

- [ ] Read QUICK_ACTION_PLAN.md
- [ ] Run quick-fix.sh
- [ ] Check output for errors
- [ ] If error: Hard refresh browser (Ctrl+Shift+R)
- [ ] If still failing: Run fix-states-dashboard.sh
- [ ] If still failing: Follow STATES_DASHBOARD_FIX_GUIDE.md Phase 1-7
- [ ] Verify at least 1 state shows data
- [ ] Check dashboard loads in < 2 seconds

### Rolling Window Implementation Checklist

**Installation**
- [ ] Copy date_utils.py to backend/app/services/
- [ ] Test import: `python3 -c "from app.services.date_utils import DateWindow; print('OK')"`

**Code Updates** (DASHBOARDS_UPDATE_GUIDE.md)
- [ ] Add import to dashboards.py
- [ ] Replace `_rolling_5_year_month_window()` calls
- [ ] Replace `_current_fy()` calls
- [ ] Test syntax: `python3 -m py_compile dashboards.py`

**Deployment**
- [ ] Set DATA_WINDOW_YEARS=5 in .env
- [ ] Rebuild: `docker compose build`
- [ ] Restart: `docker compose up -d`
- [ ] Wait 30 seconds for health checks

**Validation**
- [ ] Test API endpoints return data
- [ ] Verify yoy_trend <= 60 points
- [ ] Check logs: `docker logs trade_backend | grep -i window`
- [ ] Performance: queries should complete in < 1 second
- [ ] All dashboards show 5-year window

---

## 🔧 Commands Quick Reference

### States Dashboard
```bash
# Diagnose
bash quick-fix.sh

# Automated fix
bash fix-states-dashboard.sh

# Hard refresh browser
# Ctrl+Shift+R on http://localhost:3000/dashboards/states
```

### Rolling Window
```bash
# Copy module
cp date_utils.py backend/app/services/

# Test import
python3 -c "from app.services.date_utils import DateWindow; print(DateWindow.rolling_window())"

# Rebuild Docker
docker compose down && docker compose up -d --build

# Test endpoint
curl -H "Authorization: Bearer $TOKEN" "http://localhost:8001/api/v1/dashboards/executive" | jq .
```

### Database
```bash
# Check state data
PGPASSWORD=changeme psql -U trade -d india_trade -h localhost \
  -c "SELECT COUNT(*) FROM fact_trade_monthly WHERE state_key IS NOT NULL;"

# Run diagnostics
psql -U trade -d india_trade -h localhost < DATABASE_DIAGNOSTICS.sql
```

---

## 📞 Support & Escalation

### "My dashboard still shows empty"
1. Ensure database has state data: `SELECT COUNT(*) FROM fact_trade_monthly WHERE state_key IS NOT NULL;`
2. Check latest error: `docker logs trade_backend --tail=50`
3. Read: STATES_DASHBOARD_ARCHITECTURE.md (Section: Why Dashboard Still Shows Empty)

### "I don't understand the architecture"
1. Read: STATES_DASHBOARD_ARCHITECTURE.md (full explanation)
2. Review: Data flow section + complete query flow
3. Run SQL queries from DATABASE_DIAGNOSTICS.sql to see actual data

### "Rolling window implementation is too complex"
1. Start with: ROLLING_WINDOW_README.md (quick overview)
2. Follow: DASHBOARDS_UPDATE_GUIDE.md (copy-paste approach)
3. Use: date_utils.py (just copy the file)
4. Skip: Testing if you're in a hurry, add later

### "I broke something"
1. Check logs: `docker logs trade_backend | grep -i error`
2. Revert file: `git checkout backend/app/services/dashboards.py`
3. Restart: `docker compose down && docker compose up -d`
4. Diagnose: `bash quick-fix.sh`

---

## 📈 Success Criteria

### States Dashboard Fixed ✅
- [ ] Page loads without errors
- [ ] Shows KPI cards with data
- [ ] Shows choropleth map
- [ ] Shows bar chart
- [ ] Shows trend chart
- [ ] Click state → detail page works
- [ ] Loads in < 2 seconds

### Rolling Window Implemented ✅
- [ ] All dashboards use `DateWindow` class
- [ ] No queries use old `_rolling_5_year_month_window()`
- [ ] Data limited to 5-year window
- [ ] Queries complete in < 1 second
- [ ] Tests pass: unit + integration
- [ ] Logs show window calculations
- [ ] Configuration respected (DATA_WINDOW_YEARS)

---

## 📚 Related Documentation

These files are referenced throughout the package:
- `.env` - Environment variables configuration
- `docker-compose.yml` - Container orchestration
- `backend/app/services/dashboards.py` - Main dashboard queries
- `backend/app/core/config.py` - Application settings
- `frontend/src/app/dashboards/states/page.tsx` - Frontend component

---

## 🎓 Learning Resources

### For Understanding Date Windows
- See: `DateWindow` class in `date_utils.py` (well-commented)
- See: ROLLING_5_YEAR_IMPLEMENTATION.md (Section: Data Architecture)

### For Understanding Dashboards
- See: STATES_DASHBOARD_ARCHITECTURE.md (complete flow)
- See: Query examples in DASHBOARDS_UPDATE_GUIDE.md

### For Testing
- See: Test examples in ROLLING_5_YEAR_IMPLEMENTATION.md
- See: Test commands in quick-fix.sh and fix-states-dashboard.sh

---

## 🏁 Next Steps

1. **Choose your path** (above)
2. **Read the first document** for your path
3. **Run any scripts** as directed
4. **Follow step-by-step instructions**
5. **Test according to checklist**
6. **Commit changes to version control**
7. **Deploy when ready**

---

## 📋 Document Inventory

```
Total Files: 11
├── Markdown Documents: 8
│   ├── QUICK_ACTION_PLAN.md (6 KB)
│   ├── STATES_DASHBOARD_FIX_GUIDE.md (11 KB)
│   ├── STATES_DASHBOARD_ARCHITECTURE.md (12 KB)
│   ├── ROLLING_WINDOW_README.md (11 KB)
│   ├── ROLLING_5_YEAR_IMPLEMENTATION.md (16 KB)
│   ├── DASHBOARDS_UPDATE_GUIDE.md (9 KB)
│   └── This file: ROLLING_WINDOW_README.md
├── Code Files: 1
│   └── date_utils.py (10 KB)
├── SQL Files: 1
│   └── DATABASE_DIAGNOSTICS.sql (14 KB)
└── Bash Scripts: 2
    ├── quick-fix.sh (9 KB)
    └── fix-states-dashboard.sh (12 KB)

Total Size: ~125 KB
Estimated Read Time: 3-4 hours (all documents)
Estimated Implementation: 1-2 hours (both issues)
```

---

## ✅ Version Information

- **Created**: May 9, 2026
- **For**: India Trade Analytics Platform
- **Version**: 2.0 (States Dashboard Fix + Rolling Window)
- **Status**: Production Ready
- **Tested**: ✅ Code syntax, ✅ Docker integration, ✅ Database queries

---

**Ready to start?** Pick your path above and dive in! 🚀
