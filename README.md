# Task Manager Django Project

A simple task management application built with Django.

## Features

- Create, view, update, and delete tasks
- Mark tasks as completed
- Admin interface for data management
- Responsive UI with Bootstrap

## Project Setup

### Prerequisites

- Python 3.8+
- pip

### Installation

1. Clone the repository
2. Navigate to the project directory
3. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use venv\Scripts\activate
   ```
4. Install dependencies:
   ```
   pip install django
   ```
5. Apply migrations:
   ```
   python manage.py migrate
   ```
6. Create a superuser (for admin access):
   ```
   python manage.py createsuperuser
   ```

### Running the Application

Start the development server:
```
python manage.py runserver
```

Access the application at: http://127.0.0.1:8000/
Access the admin interface at: http://127.0.0.1:8000/admin/

## Project Structure

- `mysite/` - Main project settings
- `core/` - Task management app
  - `models.py` - Data models (Task)
  - `views.py` - View classes
  - `urls.py` - URL routing
- `templates/` - HTML templates
  - `base.html` - Base template with common layout
  - `core/` - Task-specific templates
- `static/` - Static files (CSS, JS)

## Cursor Configuration

This project includes a `.cursorrules` file that configures Cursor IDE for optimal Django development, including:

- Appropriate file/directory exclusions
- Code formatting settings
- Code snippets for Django models, views, and forms
- Search configuration optimized for Django projects 