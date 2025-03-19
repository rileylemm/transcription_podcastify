# **Optimized Analysis Prompts for YouTube Transcription Analysis**

This document contains refined prompts for **extracting valuable information** from YouTube transcriptions while removing filler.

---

## **Mistral Model Prompts (Local Model)**
Designed for technical but **not overly complex** content.

### **Technical Summary**
```
Summarize the video's technical content with a focus on:
- Core **concepts** discussed.
- **Methodologies** used or proposed.
- **Key takeaways** that someone should remember.
- Any **notable insights** that differentiate this content from common knowledge.

Organize the summary into **clear sections** with **concise bullet points** for readability.
```

### **Code Snippets & Explanations**
```
Extract **all code snippets** and provide:
1. The **exact code** (if present in transcription).
2. The **purpose** of the code in the given context.
3. A **step-by-step explanation** of how it works.
4. **Any assumptions** or dependencies needed to run it.
5. **Best practices or optimizations** if relevant.

Ensure explanations are **precise and useful for implementation**.
```

### **Tools, Libraries & Resources**
```
Extract and list **all tools, libraries, frameworks, and resources** mentioned.
For each, include:
- The **name** and a brief **description** of what it does.
- **Why it was mentioned** (e.g., problem it solves, improvement it provides).
- **Any links** given or well-known official resources.
- **Common alternatives** (if applicable).
```

### **Key Workflows & Processes**
```
Identify and outline **all workflows, methodologies, and structured processes** mentioned.
For each:
1. Provide a **step-by-step breakdown** in bullet points.
2. Highlight any **dependencies or prerequisites**.
3. Note any **best practices** or **warnings**.
4. If the workflow improves efficiency or solves a specific problem, explain how.
```

---

## **GPT-4 Model Prompts (For More Complex Topics)**
Designed for **advanced, nuanced, or high-level** technical content.

### **Advanced Technical Summary**
```
You are an **expert in technical content analysis**. Your goal is to extract **only the most valuable** insights from the video.

Summarize the content with a focus on:
- **The most critical concepts, methodologies, and techniques**.
- **Unique or advanced insights** beyond basic knowledge.
- **Real-world applications** mentioned.
- **Key takeaways** that should be remembered.

Format the output into **sections with bullet points** for clarity.
Avoid unnecessary details—focus on **actionable knowledge**.
```

### **Comprehensive Code Analysis**
```
You are a **code extraction and explanation expert**.

Extract all code snippets and provide:
1. The **full code** (if available in the transcript).
2. **What the code does** and **why it matters**.
3. A **step-by-step breakdown** of its logic.
4. **Best practices, potential pitfalls, and optimizations**.
5. Any **related concepts or frameworks** necessary for implementation.

Your goal is to provide **quick, actionable insights** for a developer reviewing this information.
```

### **Deep Dive: Tools, Libraries & Resources**
```
You are a **technical resource curator**.

Extract **all tools, libraries, and frameworks** mentioned in the video and provide:
- **Name**
- **What it does**
- **Why it was mentioned** (e.g., advantage over alternatives, use case)
- **Links if provided**
- **Related or competing technologies**

Focus on **practical utility**—omit anything that is just a passing mention without real significance.
```

### **Advanced Workflow & Process Breakdown**
```
You are a **workflow and methodology analyst**.

Identify and break down **all key workflows and structured processes** discussed in the video.
For each:
1. Provide a **step-by-step breakdown** with clear formatting.
2. Identify **critical decisions, optimizations, or best practices**.
3. Highlight **common mistakes, pitfalls, or challenges**.
4. If a workflow improves efficiency or solves a specific problem, explain **how** and **why**.

Your goal is to **help someone understand and apply** the process immediately.
```

---

### **Key Enhancements in These Prompts:**
✅ **More Precise Language** – Eliminates vague terms like "important details" and instead specifies exactly what to extract.  
✅ **Actionable Formatting** – Focuses on **bullet points, step-by-step lists, and real-world applications** to make summaries **useful for implementation**.  
✅ **Filler Reduction** – Filters out unnecessary or redundant information while **focusing only on knowledge worth retaining**.  
✅ **Better Context Extraction** – Ensures that workflows, tools, and code are **properly explained** with dependencies and best practices.  

---

Let me know if you want **further refinements** or if you have **specific pain points** with the current outputs! 🚀