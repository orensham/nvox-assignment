Here’s a **clear routing edges** from the corrected CSV

---

### **Referral & Intake**
1. **ref_karnofsky 0–39.999 → EXIT**  
   ▸ If the patient’s functional status (Karnofsky score) is below 40, they are too frail for transplant - the case exits the pathway.  

2. **ref_karnofsky 40–100 → WORKUP**  
   ▸ If the Karnofsky score is at least 40, the patient proceeds to **Baseline Workup** for full evaluation.

---

### **Baseline Workup**
3. **wrk_egfr 0–15.999 → MATCH**  
   ▸ If the patient’s kidney filtration rate (eGFR) is ≤15, they qualify for transplant listing and move to **Compatibility & Matching**.

---

### **Compatibility & Matching**
4. **mtc_pra 0–79.999 → DONOR**  
   ▸ If the Panel Reactive Antibody (PRA) level is under 80%, the recipient is immunologically suitable - proceed to **Donor Evaluation**.

5. **mtc_pra 80–100 → BOARD**  
   ▸ If PRA is 80% or higher, the patient is highly sensitized - refer directly to the **Multidisciplinary Board Review** for guidance.

---

### **Donor Evaluation**
6. **dnr_clearance=1 → BOARD**  
   ▸ If the donor passes all safety and medical clearances, advance to **Board Review** for final joint approval.

7. **dnr_clearance=0 → MATCH**  
   ▸ If the donor fails clearance, return to **Matching** to find another potential donor.

---

### **Board Review**
8. **brd_needs_more_tests=1 → WORKUP**  
   ▸ If the Board requests additional data or labs, the case returns to **Baseline Workup**.  

9. **brd_risk_score 0–6.999 → PREOP**  
   ▸ If the Board’s composite risk score is below 7, the case is approved for **Pre-Operative Optimization**.  

10. **brd_risk_score 7–10 → EXIT**  
    ▸ If the risk score is 7 or higher, the Board deems the transplant unsafe - the case exits the process.

---

### **Pre-Operative Optimization**
11. **prp_infection_status=1 → WORKUP**  
    ▸ If an unresolved infection is present, revert to **Workup** for medical stabilization.  

12. **prp_bp 60–179.999 → ORSCHED**  
    ▸ If average blood pressure is within a safe range (60–179 mmHg), proceed to **OR Scheduling & Consent**.  

13. **prp_bp 180–240 → WORKUP**  
    ▸ If blood pressure is ≥180 mmHg, optimization is needed - return to **Workup**.

---

### **OR Scheduling & Consent**
14. **ors_final_crossmatch=1 → SURG**  
    ▸ If the final immunologic crossmatch is compatible, proceed to **Transplant Surgery**.  

15. **ors_final_crossmatch=0 → PREOP**  
    ▸ If the crossmatch fails, go back to **Pre-Op Optimization** for re-assessment.

---

### **Transplant Surgery**
16. **srg_warm_isch_time 0–120 → ICU**  
    ▸ After surgery (regardless of ischemia time ≤120 min), move to **Immediate Post-Op (ICU/PACU)**.

---

### **Immediate Post-Op (ICU/PACU)**
17. **icu_airway_stable=1 → WARD**  
    ▸ If the airway is stable and the patient is extubated, transfer to **Ward Rehabilitation**.  

18. **icu_airway_stable=0 → COMPLX**  
    ▸ If the airway is unstable or complications arise, proceed to **Complication Management**.

---

### **Ward Rehabilitation & Education**
19. **wrd_walk_meters 0–149.999 → COMPLX**  
    ▸ If the patient can walk less than 150 m per day, recovery is delayed - route to **Complication Management**.  

20. **wrd_walk_meters 150–2000 → HOME**  
    ▸ If the patient walks 150 m or more daily, they are ready for **Home Monitoring**.

---

### **Home Monitoring**
21. **hom_creatinine 0.1–2.0 → HOME**  
    ▸ If serum creatinine is ≤2.0 mg/dL, graft function is stable - continue home follow-up.  

22. **hom_creatinine 2.0001–15.0 → COMPLX**  
    ▸ If creatinine rises above 2 mg/dL, a possible rejection or complication - send to **Complication Management**.

---

### **Complication Management**
23. **cpx_severity 0–4.999 → HOME**  
    ▸ Mild complications are resolved - patient can return home monitoring.  

24. **cpx_severity 5–7 → WARD**  
    ▸ Moderate complications need in-hospital rehabilitation - transfer to **Ward**.  

25. **cpx_severity 8–10 → RELIST**  
    ▸ Severe complications or graft loss - patient must be **re-listed** for transplant.

---

### **Re-Listing (Graft Failure)**
26. **rlt_new_pra 0–79.999 → MATCH**  
    ▸ If the updated PRA after graft loss is <80%, proceed directly to **Compatibility & Matching** to find a new donor.  

27. **rlt_new_pra 80–100 → BOARD**  
    ▸ If PRA ≥80%, return to **Board Review** for specialized plan due to high sensitization.

---

### **Implicit and Structural Transitions**
28. **[*] → REFERRAL**  
    ▸ Entry point: every patient starts the journey at **Referral & Intake**.  

29. **WORKUP → MATCH** (implicit via lab completion)  
    ▸ After all baseline testing and infection clearance, matching is initiated.  

30. **EXIT → [*]**  
    ▸ The process ends for patients deemed unsuitable or those who complete the journey.

---

✅ **Summary**
- **Entry:** `[ * ] → REFERRAL`
- **Normal path:** REFERRAL → WORKUP → MATCH → DONOR → BOARD → PREOP → ORSCHED → SURG → ICU → WARD → HOME  
- **Fallbacks:** any medical or logistical issue routes back to earlier stages (e.g., Workup or Complication).  
- **Loops:** HOME ↔ COMPLX ↔ WARD allow ongoing monitoring and recovery cycles.  
- **Endings:** either successful long-term follow-up at HOME or EXIT / RELIST if graft fails.
