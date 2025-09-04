# app/enums.py
ITEM_TYPES = {
    "SECTION","PROPOSITION","NO_YES_NOT_SURE","CHECKBOX","TEXT_FIELD","TEXT_FIELD_NUMERIC","TEXT_AREA",
    "MENU","MENU_MULTI_SELECT","LABEL","PICTURE","FORMULA","TIME","APPROXIMATE_DATE","APPROXIMATE_DURATION",
    "DATE","NUMERIC_SCALE","DIAGRAM","FINDING","PE_TEST","PE_CHECK","ASSESSMENT","IX","TX","RX","BILL","VIDEO","FILE_UPLOAD"
}
FIELD_VALIDATOR_TYPES = {"MANDATORY","REG_EXP","EMAIL","PHONE","POSTAL_CODE","SCRIPT"}
HINTS = {
    "USE_BUTTONS_FOR_MENU","USE_SEARCHABLE_MENU","USE_DROPDOWN_MENU","MIN_ACUITY_WEEKS","MIN_ACUITY_YEARS",
    "SAME_LINE","VERTICAL_STACKING","GREY_BG","WHITE_BG","BORDER","EXPANDED","JS_MENU_OPTION","INDIVIDUAL_MENU_OPTION"
}
FLAG_COLORS = {"NONE","RED_UNDERLINE","RED","ORANGE","YELLOW","GREEN","BLUE","PURPLE"}
NOTE_STYLES = {"PLAIN","BOLD","UNDERLINE","BOLD_UNDERLINE","ITALIC","CUSTOM"}
DATA_SECURITY_MODES = {"encrypted","anonymous","hybrid"}
NOTE_TYPES = {"progress","letter","report"}
ITEM_SUBCATEGORIES = {
    "QUESTIONNAIRE","S","HPI","PMHX","P_SURG_HX","ALLERGIES","RX","SOCIAL_HX","FAMILY_HISTORY","RISK_FACTORS",
    "RESULTS_LAB","RESULTS_IMAGING","RESULTS_TESTS","O","VITALS","GROWTH","GENERAL","HEENT","CHEST","PRECORDIAL",
    "ABDOMEN","GU","GI","PVS","NEURO","DERM","MENTAL","A","RULE_OUT","DECISION_ASSISTANCE","P","PLAN_TESTS",
    "PLAN_TESTS_TO_CONSIDER","PLAN_TX","PLAN_RX","PLAN_REFERRALS","PLAN_ADVICE","PLAN_PATIENT_RESOURCES",
    "PLAN_MONITORING","PLAN_FOLLOWUP","REFERENCE_REVIEW_ARTICLE","REFERENCE_STUDY","REFERENCE_TIP"
}
EMR_FIELDS = {
    "firstName","surname","preferredName","secondName","maidenName","title","suffix","streetNumber","address",
    "addressLine2Label","address2","city","province","country","postalCode","addr2StreetNumber","addr2Line1",
    "addr2Line2Label","addr2Line2","addr2City","addr2Province","addr2Country","addr2Postal","birthDate","email",
    "homePhone","businessPhone","businessPhoneExt","mobilePhone","pmoc","insuranceNumber","chartNumber","emergencyContact",
    "emergencyContactPhone","emergencyContactRelationship","emergencyContactIsPoA","alternateId","sex","hn","hnProv","hnVC",
    "hnExpiryDate","hnEligibility","language","emailConsent","familyClinician","referralClinician","noteFlag","familyHistory",
    "problemList","pastMedicalHistory","medications","treatments","allergies","socialHistory","riskFactors","reminders","smoker",
    "everSmoked","cigsPerDay","packYears","smokesCigars","smokesPipe","chewsTobacco","vapes","secondHandSmoke","drinksPerWeek",
    "cannabisUse","occupation"
}
