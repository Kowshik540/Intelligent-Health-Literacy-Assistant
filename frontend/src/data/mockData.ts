import type { ApiResponse } from "../types";

export const mockResponses: Record<string, ApiResponse> = {
  hypertension: {
    answer:
      "Hypertension is often asymptomatic, meaning many people may not notice any symptoms. When symptoms do occur, they can be nonspecific. Blood pressure measurement is important because symptoms alone cannot reliably identify hypertension.",
    plain:
      "High blood pressure often does not cause noticeable symptoms. The only reliable way to know if someone has high blood pressure is to have their blood pressure measured.",
    source: "Hypertension Clinical Guidelines",
    institution: "Verified Clinical Reference",
    page: "14",
    totalPages: "148",
    section: "Symptoms & Diagnosis",
    snippet:
      "Hypertension is frequently asymptomatic and may not produce noticeable symptoms. Blood pressure measurement is required to identify elevated blood pressure.",
    confidence: "DEMO 98.7%",
  },

  "what is hypertension": {
    answer:
      "Hypertension refers to persistently elevated blood pressure. It is frequently asymptomatic, which is why regular blood pressure measurement is important.",
    plain:
      "Hypertension means blood pressure stays higher than it should. Many people do not feel anything, so checking blood pressure is important.",
    source: "Hypertension Clinical Guidelines",
    institution: "Verified Clinical Reference",
    page: "12",
    totalPages: "148",
    section: "Definition",
    snippet:
      "Hypertension is defined by persistently elevated blood pressure and is frequently asymptomatic.",
    confidence: "DEMO 98.9%",
  },

  "myocardial infarction": {
    answer:
      "Myocardial infarction, commonly called a heart attack, occurs when blood flow to part of the heart muscle becomes blocked. It is a serious medical condition requiring urgent medical attention.",
    plain:
      "A myocardial infarction is a heart attack. It happens when part of the heart does not get enough blood because blood flow is blocked. Emergency medical care may be needed.",
    source: "Cardiovascular Clinical Guidelines",
    institution: "Verified Clinical Reference",
    page: "27",
    totalPages: "116",
    section: "Acute Coronary Syndromes",
    snippet:
      "Myocardial infarction results from acute interruption of blood flow to the myocardium and requires immediate clinical assessment.",
    confidence: "DEMO 99.1%",
  },

  "what is myocardial infarction": {
    answer:
      "Myocardial infarction, commonly known as a heart attack, occurs when blood flow to part of the heart muscle becomes blocked.",
    plain:
      "A myocardial infarction is a heart attack caused by blocked blood flow to part of the heart.",
    source: "Cardiovascular Clinical Guidelines",
    institution: "Verified Clinical Reference",
    page: "27",
    totalPages: "116",
    section: "Acute Coronary Syndromes",
    snippet:
      "Myocardial infarction results from acute interruption of blood flow to the myocardium.",
    confidence: "DEMO 99.1%",
  },

  diabetes: {
    answer:
      "Diabetes is a chronic condition involving elevated blood glucose levels. Depending on the type and severity, people may experience increased thirst, frequent urination, fatigue, or other symptoms. Diagnosis requires appropriate clinical testing.",
    plain:
      "Diabetes is a long-term condition where blood sugar stays too high. Some people may feel very thirsty, urinate often, or feel tired, but testing is needed for diagnosis.",
    source: "Diabetes Management Guidelines",
    institution: "Verified Clinical Reference",
    page: "31",
    totalPages: "92",
    section: "Clinical Presentation",
    snippet:
      "Diabetes is characterized by elevated blood glucose resulting from impaired insulin secretion, impaired insulin action, or both.",
    confidence: "DEMO 97.9%",
  },

  "what is diabetes": {
    answer:
      "Diabetes is a chronic condition involving elevated blood glucose levels. Depending on the type and severity, people may experience increased thirst, frequent urination, fatigue, or other symptoms. Diagnosis requires appropriate clinical testing.",
    plain:
      "Diabetes is a long-term condition where blood sugar stays too high. Some people may feel very thirsty, urinate often, or feel tired, but testing is needed for diagnosis.",
    source: "Diabetes Management Guidelines",
    institution: "Verified Clinical Reference",
    page: "31",
    totalPages: "92",
    section: "Clinical Presentation",
    snippet:
      "Diabetes is characterized by elevated blood glucose resulting from impaired insulin secretion, impaired insulin action, or both.",
    confidence: "DEMO 97.9%",
  },
};

export const SOURCES = [
  {
    title: "Clinical Practice Guidelines",
    category: "Medical Guideline",
    pages: "148 pages",
    year: "2025",
    institution: "Verified Clinical Reference",
  },
  {
    title: "Hypertension Management",
    category: "Clinical Reference",
    pages: "92 pages",
    year: "2025",
    institution: "Verified Clinical Reference",
  },
  {
    title: "Cardiovascular Health",
    category: "Institutional Guideline",
    pages: "116 pages",
    year: "2024",
    institution: "Verified Clinical Reference",
  },
  {
    title: "Patient Safety Standards",
    category: "Safety Guideline",
    pages: "74 pages",
    year: "2025",
    institution: "Verified Clinical Reference",
  },
];

export const safetyModules = [
  {
    name: "PII Detection",
    detail: "Personal information filtering",
  },
  {
    name: "High-Risk Detection",
    detail: "Clinical risk classification",
  },
  {
    name: "Clinical Refusal",
    detail: "Unsafe advice prevention",
  },
  {
    name: "Source Verification",
    detail: "Claim-to-source matching",
  },
];

export const MODULES = [
  {
    icon: "◈",
    title: "Evidence Retrieval",
    detail: "Prototype · Ready",
  },
  {
    icon: "◇",
    title: "Citation Verification",
    detail: "Claim validation",
  },
  {
    icon: "◉",
    title: "Safety Guardrails",
    detail: "Risk detection",
  },
];