import streamlit as st
import pyodbc
import requests

#  Hugging Face API Key 
HUGGINGFACE_API_KEY = "Your_API_KEY"

#  Database Connection 
def create_database_connection(database="RecipeDB"):
    try:
        drivers = [driver for driver in pyodbc.drivers() if "SQL Server" in driver]
        if not drivers:
            st.error("No SQL Server ODBC Driver found. Install ODBC Driver 17 or 18.")
            st.stop()

        driver = drivers[0]
        connection_string = f"""
            DRIVER={{{driver}}};
            SERVER=LAPTOP-D60U7FED\\SQLEXPRESS01;
            DATABASE={database};
            Trusted_Connection=yes;
        """
        conn = pyodbc.connect(connection_string, timeout=5)
        conn.autocommit = True
        return conn

    except pyodbc.Error as ex:
        st.error(f"Database connection failed: {ex}")
        st.stop()

#  Setup Database 
def setup_database():
    try:
        master_conn = create_database_connection("master")
        master_cursor = master_conn.cursor()

        master_cursor.execute("""
            IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'RecipeDB')
            BEGIN
                CREATE DATABASE RecipeDB;
            END
        """)

        conn = create_database_connection("RecipeDB")
        cursor = conn.cursor()
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'recipes')
            BEGIN
                CREATE TABLE recipes (
                    id INT PRIMARY KEY IDENTITY(1,1),
                    category NVARCHAR(100),
                    ingredient NVARCHAR(500),
                    action NVARCHAR(100),
                    steps NVARCHAR(MAX),
                    created_at DATETIME DEFAULT GETDATE()
                );
            END
        """)
        return conn
    except pyodbc.Error as ex:
        st.error(f"Database setup failed: {ex}")
        st.stop()

#  Hugging Face Detailed Recipe Generator 
def generate_detailed_recipe(ingredients, action, category):
    ingredients_str = ", ".join(ingredients)
    prompt = (
        f"You are a professional chef. Write a detailed, step-by-step cooking recipe for a {category} dish "
        f"that uses the following ingredients: {ingredients_str}. The dish must involve the action: '{action}'.\n\n"
        "Include:\n"
        "- A title for the recipe\n"
        "- An ingredients list\n"
        "- Cooking time\n"
        "- Number of servings\n"
        "- Step-by-step instructions (at least 5 steps, numbered)\n"
        "- Serve suggestion\n"
        "Make sure each step includes specific actions, ingredients, and any temperatures or durations.\n\n"
        "Here is the recipe:\n"
    )

    api_url = "https://api-inference.huggingface.co/models/HuggingFaceH4/zephyr-7b-beta"
    headers = {
        "Authorization": f"Bearer {HUGGINGFACE_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_length": 1024,
            "do_sample": True,
            "temperature": 0.7,
            "top_p": 0.9
        }
    }

    response = requests.post(api_url, headers=headers, json=payload)

    if response.status_code == 200:
        result = response.json()
        return result[0]['generated_text'].replace(prompt, "")
    else:
        return f"⚠️ Error from Hugging Face API: {response.status_code} - {response.text}"

#  Initialize App 
conn = setup_database()
cursor = conn.cursor()
st.set_page_config(page_title="Smart Recipe Generator", layout="wide")

#  Background Image CSS 
def add_food_background():
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("https://images2.alphacoders.com/912/thumb-1920-912814.jpg");
            background-attachment: fixed;
            background-size: cover;
            background-position: center center;
        }}
        .title {{
            color: black;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

add_food_background()

st.markdown('<h1 class="title">Smart Recipe Generator</h1>', unsafe_allow_html=True)

# Sidebar
st.sidebar.header("Choose Your Ingredients")
ingredients = [
    "Eggs", "Potato", "Tomato", "Rice", "Milk", "Flour", "Onion", "Garlic", "Carrot", 
    "Spinach", "Paneer", "Chicken", "Fish", "Mushroom", "Beans", "Broccoli", "Capsicum", 
    "Cabbage", "Cheese", "Corn", "Lentils", "Tofu", "Peas", "Beetroot", "Pumpkin", 
    "Cauliflower", "Bread", "Yogurt", "Coconut", "Butter", "Chili", "Cucumber", 
    "Sweet Potato", "Zucchini", "Bell Pepper", "Mint", "Basil", "Lemon", "Ginger"
]

selected_ingredients = st.sidebar.multiselect("Select Ingredients", ingredients)

categories = ["Breakfast", "Meals", "Snacks", "Dessert", "Appetizers", "Soups & Stews", 
    "Salads", "Sauces & Dips", "Smoothies & Juices", "Side Dishes", "Main Course", 
    "Vegetarian", "Vegan", "Gluten-Free", "Low-Carb", "Keto", "High-Protein", 
    "Pasta", "Pizza", "Bread & Baked Goods", "Sweets & Treats", "Drinks", 
    "Crockpot/Slow Cooker", "Instant Pot", "Grilled", "Stir-fry", "One-Pot Meals", 
    "Fermented Foods", "Healthy Snacks"]

selected_category = st.sidebar.selectbox("Category", categories)

actions = [
    "boil", "fry", "bake", "grill", "mix", 
    "sauté", "steam", "roast", "blanch", 
    "stir-fry", "slow-cook", "poach", "simmer", "braise",
    "broil", "deep-fry", "pan-fry", "barbecue", "marinate",
    "steam", "grate", "chop", "mash", "whisk", 
    "glaze", "grind", "caramelize", "zest", "fold", 
    "shred", "press", "crush", "toast", "microwave", 
    "blend", "stir", "tenderize", "freeze", "thaw"
]

selected_action = st.selectbox("What are you doing with the ingredient?", actions)

# Generate Recipe
if st.button("Generate Recipe"):
    if not selected_ingredients:
        st.error("Please select at least one ingredient.")
    else:
        loading_msg = "<p style='color: black; font-weight: bold;'>Whipping up a mouth-watering recipe just for you...</p>"
        loading_placeholder = st.empty()
        loading_placeholder.markdown(loading_msg, unsafe_allow_html=True)

        with st.spinner(" "):
            search_terms = [ingredient.lower() for ingredient in selected_ingredients]
            cursor.execute("""
                SELECT steps FROM recipes
                WHERE LOWER(ingredient) = ?
                AND LOWER(action) = ?
            """, (", ".join(search_terms), selected_action.lower()))
            result = cursor.fetchone()

            if result:
                steps = result[0]
            else:
                steps = generate_detailed_recipe(selected_ingredients, selected_action, selected_category)
                if steps:
                    cursor.execute("""
                        INSERT INTO recipes (category, ingredient, action, steps)
                        VALUES (?, ?, ?, ?)
                    """, (selected_category, ", ".join(selected_ingredients), selected_action, steps))
                    conn.commit()

            loading_placeholder.empty()
            st.subheader(f"Recipe Steps for {', '.join(selected_ingredients)} ({selected_action})")
            st.markdown(f"""<div style='white-space: pre-wrap; background-color: rgba(255, 255, 255, 0.8); color: black; padding: 1rem; border-radius: 10px;'>
            {steps}</div>""", unsafe_allow_html=True)
