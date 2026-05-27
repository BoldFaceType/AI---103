TL;DR  
This sprint plan establishes a high-velocity, 4-week study structure targeting the Azure AI-102 certification by June 28, 2026. It applies the Rule of One (focusing strictly on passing the exam via hands-on execution) and rejects theoretical bloat. Each block balances the Core Four primitives across Azure AI services, optimized for your local/hybrid stack.

The Vetting Protocol (VCR & KISS)  
We are not reading 500-page whitepapers. We are treating the AI-102 objectives as automation endpoints. The target is to maximize the Value-to-Complexity Ratio (VCR) by mapping Azure SDKs directly to functional code scripts inside your WSL2/Ubuntu environment, bypassing unnecessary portal clicking where a terminal command works faster.

4-Week Sprint Control Flow  
[Week 1: Cognitive & Vision Services] --> [Week 2: NLP & Document Intelligence]  
                                                   |  
                                                   v  
[Week 4: Final Drills & Exam Day]     <-- [Week 3: Knowledge Mining & Azure OpenAI]  
Data & Control Flow Chart: Weekly Execution Loop

       +---------------------------------------------+  
       |   Monday: Map AI-102 Domain to Context      |  
       +---------------------------------------------+  
                              |  
                              v  
       +---------------------------------------------+  
       |   Tue-Thu: Build Raw Python Scripts / Tools |  
       +---------------------------------------------+  
                              |  
                              v  
       +---------------------------------------------+  
       |   Friday: Negative Space Refactoring & Labs |  
       +---------------------------------------------+  
                              |  
                              v  
       +---------------------------------------------+  
       |   Saturday: Practice Questions (Measure VCR)|  
       +---------------------------------------------+

Detailed Study Blocks  
Week 1: Computer Vision & Edge Integration (Value: High | Complexity: Moderate)  
Focus: Azure AI Vision, Custom Vision, and Video Indexer.

Core Four Mapping:

Context: Image/Video binary payloads, camera streams.

Model: Azure Vision API backends.

Prompt/Config: JSON analysis features (Tags, OCR, Objects).

Tools: Python SDK (azure-cognitiveservices-vision-computervision).

Execution Task: Write a unified script following your file naming convention: Create_VisionAnalysis_WSL.py. Connect it to a mock local directory to simulate local-first ingestion.

Week 2: Language Processing & Document Intelligence (Value: High | Complexity: High)  
Focus: Azure AI Language, Translation, and Document Intelligence (Form Recognizer).

Core Four Mapping:

Context: Unstructured medical notes/text, PDF medical records (aligned with your ClinicalAI-Verifier portfolio goals).

Model: Azure Language & Document Models.

Prompt/Config: Named Entity Recognition (NER) schemas, Custom extraction models.

Tools: Azure Document Intelligence SDK.

Execution Task: Build Extract_MedicalText_Clinical.py. Feed it structured and unstructured text to verify handling of PII and medical entities.

Week 3: Knowledge Mining & Azure OpenAI Orchestration (Value: Critical | Complexity: High)  
Focus: Azure AI Search (formerly Cognitive Search) and Azure OpenAI Service tokens/deployments.

Core Four Mapping:

Context: Vector indexes, chunked documents.

Model: gpt-4o, text-embedding-3-large.

Prompt: System instructions enforcing strict boundaries (KISS).

Tools: Azure AI Search SDK, OpenAI Python SDK client.

Execution Task: Build a deterministic RAG script Query_VectorSearch_Azure.py. Maximize output tokens dedicated to API tool definitions to mirror parallel agentic architectures.

Week 4: Precision Refinement & Exam Simulation (Value: Maximum | Complexity: Low)  
Focus: Edge deployment (IoT Edge containers), Responsible AI compliance, and practice exams.

Execution Task: Run full-length practice tests. Use the Negative Space paradigm here: eliminate incorrect answers ruthlessly based on Azure documentation constraints rather than guessing the "right" answer.

Next Steps  
Confirm if this structure aligns with your current daily bandwidth so we can micro-task the specific Azure CLI commands for Week 1 environment initialization.
