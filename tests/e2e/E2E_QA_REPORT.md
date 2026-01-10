# E2E QA Test Report - Odoo MCP Server (Comprehensive)

**Report Date:** 2026-01-10
**Test Environment:** Staging (ODOO staging connector in Claude.ai)
**Tester:** Claude Code E2E QA Manager
**Test Method:** Claude.ai Chrome Integration with MCP tools
**OAuth Client ID:** 360932891826-6b82gjn5igtfihefq5cf68i45iquhtr9.apps.googleusercontent.com
**Test User:** jiri.manas@keboola.com (Jiri Manas - CTO)

---

## Executive Summary

This report documents comprehensive E2E testing of the Odoo MCP Server integration with Claude.ai, covering **62 test scenarios** across all employee self-service functions.

### Overall Status: **BLOCKED - CRITICAL PERFORMANCE ISSUES**

🚨 **CRITICAL:** MCP server is experiencing severe performance degradation:
- Tool calls taking 30-90+ seconds (expected: <5 seconds)
- Intermittent connection errors occurring
- Some tool calls timing out completely
- Server appears to have cold start latency issues

| Category | Total | Pass | Fail | Error/Timeout | Pending | Requires Staging |
|----------|-------|------|------|---------------|---------|------------------|
| Setup & Auth | 4 | 4 | 0 | 0 | 0 | 0 |
| Profile & Organization | 12 | 2 | 0 | 2 | 8 | 0 |
| Leave Management | 22 | 1 | 0 | 1 | 20 | 8 |
| Documents | 12 | 0 | 0 | 1 | 11 | 0 |
| Error Handling | 12 | 0 | 0 | 0 | 12 | 0 |
| **TOTAL** | **62** | **7** | **0** | **4** | **51** | **8** |

---

## Staging Data Requirements

### Required Before Extended Testing

| Data | Status | Notes |
|------|--------|-------|
| Employee records | ✅ Ready | 97 employees |
| PTO allocations | ✅ Ready | 25 days for 2026 |
| Sick Leave allocation | ❌ Not configured | 10 days needed |
| Unpaid Leave type | ❌ Not configured | Enable in Odoo |
| Public Holidays 2026 | ❌ Not configured | CZ/company holidays |
| HR Documents | ✅ Ready | 5 docs in 2 categories |

---

## Test Execution Summary

### Setup Tests (S01-S04)

| ID | Name | Status | Result |
|----|------|--------|--------|
| S01 | Verify Login | ✅ Pass | User logged in as jiri.manas@keboola.com |
| S02 | Add MCP Server | ✅ Pass | Odoo MCP Staging connector present in org |
| S03 | OAuth Connect | ✅ Pass | Google OAuth flow completed, redirect_uri fixed |
| S04 | Verify Tools | ✅ Pass | MCP tools available (Configure button visible) |

### Profile Tests (P01-P12)

| ID | Name | Tool | Status | Result |
|----|------|------|--------|--------|
| P01 | Get My Profile | get_my_profile | ✅ Pass | Name: Jiri Manas, Title: CTO, Dept: Leadership, Division: Operations, Email: jiri.manas@keboola.com, Phone: +420 724 253 175, Manager: Pavel Doležal, Coach: Pavel Doležal |
| P02 | Get My Manager | get_my_manager | ✅ Pass | Name: Pavel Doležal, Title: Co-Founder and CEO, Dept: Leadership, Email: pavel.dolezal@keboola.com, Phone: +602 654 654 |
| P03 | Get My Team | get_my_team | ⏳ Slow | Request timed out due to server latency (~60s+) |
| P04 | Find Colleague | find_colleague | ⏳ Pending | - |
| P05 | Find by Department | search_employees | ⏳ Pending | - |
| P06 | Get Direct Reports | get_direct_reports | ⏳ Pending | - |
| P07 | Update Contact | update_my_contact | ⏳ Pending | - |
| P08 | Search Directory | search_employees | ⏳ Pending | - |
| P09 | Custom Fields | get_my_profile | ⏳ Pending | - |
| P10 | Coach Info | get_my_profile | ⏳ Pending | - |
| P11 | Find All Managers | search_records | ⏳ Pending | - |
| P12 | Revert Contact | update_my_contact | ⏳ Pending | - |

### Leave Tests (L01-L22)

| ID | Name | Tool | Status | Requires Staging |
|----|------|------|--------|------------------|
| L01 | Get Leave Balance | get_my_leave_balance | ⏳ Pending | - |
| L02 | Specific Balance (Sick) | get_my_leave_balance | ⏳ Pending | Sick leave |
| L03 | Leave History | get_my_leave_requests | ⏳ Pending | - |
| L04 | Pending Leave | get_my_leave_requests | ⏳ Pending | - |
| L05 | Upcoming Leave | get_my_leave_requests | ⏳ Pending | - |
| L06 | Request Vacation | request_leave | ⏳ Pending | - |
| L07 | Request Sick | request_leave | ⏳ Pending | Sick leave |
| L08 | Request Half Day | request_leave | ⏳ Pending | - |
| L09 | Cancel Leave | cancel_leave_request | ⏳ Pending | - |
| L10 | Team Availability | search_holidays | ⏳ Pending | - |
| L11 | Public Holidays | get_public_holidays | ⏳ Pending | Holidays |
| L12 | Leave with Reason | request_leave | ⏳ Pending | - |
| L13 | Request Unpaid | request_leave | ⏳ Pending | Unpaid leave |
| L14 | All Leave Balances | get_my_leave_balance | ⏳ Pending | - |
| L15 | Sick Same Day | request_leave | ⏳ Pending | Sick leave |
| L16 | Multi-Day Sick | request_leave | ⏳ Pending | Sick leave |
| L17 | Leave Over Holiday | request_leave | ⏳ Pending | Holidays |
| L18 | Holiday in Range | get_public_holidays | ⏳ Pending | Holidays |
| L19 | Year Holidays | get_public_holidays | ⏳ Pending | Holidays |
| L20 | Single Day Leave | request_leave | ⏳ Pending | - |
| L21 | Balance After Request | get_my_leave_balance | ⏳ Pending | - |
| L22 | Multiple Pending | get_my_leave_requests | ⏳ Pending | - |

### Document Tests (D01-D12)

| ID | Name | Tool | Status | Result |
|----|------|------|--------|--------|
| D01 | Document Categories | get_document_categories | ⏳ Pending | - |
| D02 | List All Documents | get_my_documents | ⏳ Pending | - |
| D03 | List Contracts | get_my_documents | ⏳ Pending | - |
| D04 | List Identity Docs | get_my_documents | ⏳ Pending | - |
| D05 | Download Document | download_document | ⏳ Pending | - |
| D06 | Upload Identity | upload_identity_document | ⏳ Pending | - |
| D07 | Document Details | get_document_details | ⏳ Pending | - |
| D08 | Expiring Documents | get_my_documents | ⏳ Pending | - |
| D09 | Upload ID Card | upload_identity_document | ⏳ Pending | - |
| D10 | Upload Driving License | upload_identity_document | ⏳ Pending | - |
| D11 | Document Count | get_document_categories | ⏳ Pending | - |
| D12 | Recent Documents | get_my_documents | ⏳ Pending | - |

### Error Tests (E01-E12)

| ID | Name | Expected Error | Status |
|----|------|----------------|--------|
| E01 | Invalid Employee | "Employee not found" | ⏳ Pending |
| E02 | Overlapping Dates | "Dates overlap" | ⏳ Pending |
| E03 | Insufficient Balance | "Insufficient balance" | ⏳ Pending |
| E04 | Cancel Approved | "Cannot cancel" | ⏳ Pending |
| E05 | Access Denied | "Access denied" | ⏳ Pending |
| E06 | Invalid Dates | "Invalid date" | ⏳ Pending |
| E07 | End Before Start | "End date before start" | ⏳ Pending |
| E08 | Past Date Request | "Past date" error | ⏳ Pending |
| E09 | Invalid Leave Type | "Leave type not found" | ⏳ Pending |
| E10 | Cancel Non-Existent | "Request not found" | ⏳ Pending |
| E11 | Empty Document Upload | "No content" error | ⏳ Pending |
| E12 | Invalid Document Type | "Invalid type" error | ⏳ Pending |

---

## Known Limitations

| Feature | Status | Notes |
|---------|--------|-------|
| Half-day leave | Not supported | Odoo limitation - full days only |
| Leave approval workflow | Read-only | Cannot approve via MCP |
| Document expiry dates | Partial | Depends on Odoo DMS config |

---

## Test Coverage Summary

| Metric | Previous | Current Target |
|--------|----------|----------------|
| Tests Defined | 40 | 62 |
| Tests Executed | 15 | 0 (reset) |
| Coverage % | 37.5% | Target: 100% |
| Leave Types Tested | 1 (PTO) | Target: 3 (PTO, Sick, Unpaid) |
| Error Tests | 0 | Target: 12 |

---

## Execution Notes

**Test execution order:**
1. Setup tests (S01-S04) - ✅ COMPLETED
2. Profile tests (P01-P12) - 🔄 IN PROGRESS (2/12 complete)
3. Leave tests - PTO only (L01, L03-L06, L09, L12, L14, L20-L22)
4. Leave tests - Requires staging (L02, L07, L11, L13, L15-L19)
5. Document tests (D01-D12)
6. Error tests (E01-E12)

**Staging configuration completed:**
1. ✅ Sick Leave allocation - Configured
2. ✅ Unpaid Leave type - Enabled
3. ✅ Public holidays for 2026 - Configured

**Issues Encountered:**
1. **OAuth redirect_uri mismatch** - Fixed by adding `https://claude.ai/api/mcp/auth_callback` to GCP OAuth client
2. **MCP Server Performance** - Tool calls taking 30-60+ seconds, causing timeouts during testing

---

## Test Session Log

### Session 1 - 2026-01-08

**Environment:**
- Claude.ai with Opus 4.5
- Odoo MCP Staging connected via Google OAuth
- Test user: jiri.manas@keboola.com

**Results:**
- S01-S04: All setup tests PASSED
- P01: Get My Profile - PASSED (returned full profile data)
- P02: Get My Manager - PASSED (returned Pavel Doležal info)
- P03: Get My Team - TIMEOUT (server latency issue)

---

### Session 2 - 2026-01-10

**Environment:**
- Claude.ai with Haiku 4.5 (also tested with Opus 4.5)
- ODOO staging connector configured in Claude.ai organization
- Test user: jiri.manas@keboola.com

**Pre-Test Setup Verification:**
- ✅ Claude.ai login verified
- ✅ ODOO staging connector found and connected
- ✅ **23 MCP tools available** (exceeds expected 19+)

**Tools Verified:**
cancel_leave_request, count_records, create_record, delete_record, download_document, find_colleague, get_direct_reports, get_document_categories, get_document_details, get_my_documents, get_my_leave_balance, get_my_leave_requests, get_my_manager, get_my_profile, get_my_team, get_public_holidays, get_record, list_models, request_leave, search_records, update_my_contact, update_record, upload_identity_document

**Test Results:**

| Test ID | Test Name | Tool | Status | Response Time | Notes |
|---------|-----------|------|--------|---------------|-------|
| S04 | Verify Tools | - | ✅ PASS | <2s | 23 tools visible in connector config |
| P01 | Get My Profile | get_my_profile | ✅ PASS | ~8s | Full profile: Jiri Manas, CTO, Leadership, jiri.manas@keboola.com, +420724253175, Manager: Pavel Doležal |
| P02 | Get My Manager | get_my_manager | ⚠️ ERROR | 60s+ | Tool error with recovery - Claude provided cached manager info |
| L01 | Get Leave Balance | get_my_leave_balance | ✅ PASS | ~8s | 25 days PTO remaining for 2026 |
| L01 | Get Leave Balance (retry) | get_my_leave_balance | ❌ ERROR | - | "Odoo system returning error" - intermittent failure |
| D01 | Document Categories | get_document_categories | ❌ TIMEOUT | 70s+ | Request never completed |

**Critical Issues Observed:**

1. **Severe Latency (P0 - Blocker)**
   - Tool calls averaging 30-90+ seconds
   - Multiple requests timing out completely
   - "A bit longer, thanks for your patience..." message appearing frequently
   - Impact: Testing cannot proceed efficiently

2. **Intermittent Errors (P1 - High)**
   - Same tool (get_my_leave_balance) succeeds sometimes, fails others
   - Error message: "The Odoo system is returning an error when trying to fetch your leave balance"
   - Suggests connection instability or resource contention

3. **Tool Error Recovery (P2 - Medium)**
   - get_my_manager showed error icon but Claude provided fallback answer
   - This is good UX but indicates underlying tool issues

4. **Health Endpoint (P2 - Medium)**
   - Health check at documented URL returns 404
   - URL may have changed or endpoint not configured

**Performance Comparison:**

| Test | Expected Time | Actual Time | Status |
|------|---------------|-------------|--------|
| get_my_profile | <3s | 8s | ⚠️ Slow |
| get_my_leave_balance | <3s | 8s | ⚠️ Slow |
| get_my_manager | <3s | 60s+ timeout | ❌ Failed |
| get_document_categories | <3s | 70s+ timeout | ❌ Failed |

**Recommendations:**

1. **Immediate Actions:**
   - Investigate Cloud Run cold start times
   - Check Odoo connection pooling configuration
   - Review server logs for timeout causes
   - Consider increasing instance min-count to prevent cold starts

2. **Before Next Test Session:**
   - Fix latency issues (target: <5s per tool call)
   - Verify health endpoint configuration
   - Add connection health monitoring

3. **Testing Blocked Until:**
   - Performance stabilized at acceptable levels
   - Intermittent errors resolved

---

## Appendix: Functional Test Results (When Tools Respond)

When the MCP server responds successfully, the tools return correct data:

### P01 - Get My Profile (PASSED)
```
Name: Jiri Manas
Job Title: Chief Technology Officer (CTO)
Department: Leadership
Division: Operations
Work Email: jiri.manas@keboola.com
Mobile Phone: +420724253175
Manager: Pavel Doležal
Coach: Pavel Doležal
```

### L01 - Get Leave Balance (PASSED)
```
Leave Type: Paid Time Off
Allocated: 25 days
Taken: 0 days
Remaining: 25 days
Year: 2026
```

---

*Report initialized: 2026-01-04*
*Last updated: 2026-01-10*
*Status: BLOCKED - Critical performance issues preventing comprehensive testing*
