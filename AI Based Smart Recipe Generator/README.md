Here is a clean, well-structured **README.md** for your GitHub project.
It explains features, setup, installation, environment variables, usage, and more.

---

# 🧑‍🍳 Recipe Generator (Streamlit + Gemini Vision + PDF Export)

A powerful **AI-based Recipe Generator** built with **Streamlit**, **Google Gemini Vision**, and **ReportLab**.
This app lets you:

✔️ **Type ingredients** to generate a complete recipe
✔️ **Upload a food photo** → Gemini Vision identifies the dish + ingredients
✔️ **Auto-scaled ingredient quantities** (1–45 servings)
✔️ **Download recipe as PDF**
✔️ Works for all cuisines & dish types

---

## 🚀 Features

### 🔍 1. Generate Recipes From Text

Enter comma-separated ingredients and get:

* Dish name
* Ingredients list (auto-scaled by servings)
* Cooking steps
* Cuisine customization

### 📸 2. Generate Recipes From Image (AI Vision)

Upload a picture of your dish.
Gemini:

* Identifies the dish
* Extracts possible ingredients
* Generates full recipe

### 📄 3. Download as PDF

The entire recipe can be saved offline as a neat PDF using **ReportLab**.

### 🍽 4. Quantity Scaling (Up to 45 Servings!)

Ingredients auto-scale based on real-world estimates.

---

## 🛠️ Tech Stack

* **Python 3.10+**
* **Streamlit** (UI)
* **Google Gemini API (google-generative-ai)**
* **Pillow**
* **ReportLab** (PDF generation)
* **dotenv** (API key handling)

---

## 📦 Installation

### 1️⃣ Clone the repository

```bash
git clone https://github.com/yourusername/recipe-generator.git
cd recipe-generator
```

### 2️⃣ Install required packages

```bash
pip install -r requirements.txt
```

Or install manually:

```
streamlit
pillow
python-dotenv
google-generativeai
reportlab
```

---

## 🔑 Setup Google Gemini API Key

### Step 1: Visit

👉 [https://aistudio.google.com](https://aistudio.google.com)
Login → Go to **API Keys**

### Step 2: Create a new key

Click **Create API Key** → Copy

### Step 3: Add key to `.env` file

Create a file named:

```
.env
```

Put this inside:

```
GOOGLE_API_KEY=YOUR_API_KEY_HERE
```

---

## ▶️ Run the App

```bash
streamlit run app.py
```

The app will open in your browser at:

```
http://localhost:8501
```

---

## 📷 Example Flow (Image → Recipe)

1. Upload a food image
2. Gemini Vision detects dish (e.g., *Masala Potatoes*)
3. Ingredients auto-generated
4. Ingredients scale if you choose more servings
5. Steps generated automatically
6. Download the PDF

---

## 📄 PDF Output Includes:

* Recipe title
* Cuisine & meal type
* Ingredients (auto-scaled)
* Steps
* Clean readable formatting

---

## 📁 Project Structure

```
recipe-generator/
│── app.py
│── requirements.txt
│── README.md
│── .env (you create)
│── /images (optional)
```

---

## 🧪 Troubleshooting

### ❌ INVALID API KEY

If you see:

```
InvalidArgument: API key not valid
```

Check:
✔ API key copied correctly
✔ .env file created
✔ Restart terminal after adding .env
✔ `GOOGLE_API_KEY` is NOT expired
✔ Billing is optional but available

### ❌ “Unable to process input image”

Make sure:

* Upload only `jpg/png`
* Image size not corrupted
* Try another image

---

## 🤝 Contributing

Pull requests are welcome!
You can enhance the app with:

* More advanced ingredient scaling
* More cuisines
* UI themes
* Storage / recipe history

---

## 📜 License

This project is open-source under the **MIT License**.

---

If you want, I can:
✅ Add screenshots to README
✅ Generate `requirements.txt`
✅ Create GitHub project description
Just tell me!
