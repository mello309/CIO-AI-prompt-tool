# Gemini Prompt Runner

A web application that allows your team to run premade prompts using Google's Gemini AI. Perfect for code reviews, documentation generation, bug fixing, and more.

## Features

- 🚀 **Premade Prompts**: Pre-configured prompts for common tasks like code review, documentation, bug fixing
- 🎯 **Easy to Use**: Simple web interface for running prompts
- ⚙️ **Customizable**: Add your own custom prompts
- 👥 **Team-Friendly**: Share prompts across your team
- 🔧 **Gemini Integration**: Powered by Google's Gemini AI

## Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Get Gemini API Key**
   - Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Create a new API key
   - Copy the API key

3. **Configure Environment**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and add your Gemini API key:
   ```
   GEMINI_API_KEY=your-actual-api-key-here
   SECRET_KEY=your-secret-key-here
   ```

4. **Run the Application**
   ```bash
   python app.py
   ```

5. **Access the App**
   Open your browser and go to `http://localhost:5000`

## Usage

### Running Prompts
1. Select a prompt type from the dropdown
2. Enter your input (code, text, etc.)
3. Click "Run Prompt" to get Gemini's response

### Adding Custom Prompts
1. Go to "Manage Prompts" in the navigation
2. Fill in the form with your custom prompt details
3. Use `{user_input}` as a placeholder in your prompt template
4. Save and use your new prompt

## Built-in Prompts

- **Code Review Assistant**: Analyzes code for bugs, best practices, and improvements
- **Documentation Generator**: Creates comprehensive documentation for code
- **Bug Fix Assistant**: Helps identify and fix bugs
- **Code Refactoring**: Suggests improvements and refactoring
- **Code Explainer**: Explains complex code in simple terms

## Customization

You can easily add more prompts by:
1. Editing the `PREMADE_PROMPTS` dictionary in `app.py`
2. Using the web interface to add prompts dynamically
3. Modifying the templates to add new features

## Team Features

- Share prompts across team members
- Consistent AI responses using the same prompts
- Easy prompt management and updates

## Requirements

- Python 3.7+
- Flask
- Google Generative AI library
- Gemini API key

## License

MIT License - feel free to use and modify for your team's needs!
