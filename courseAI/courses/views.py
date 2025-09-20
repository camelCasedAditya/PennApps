import os
import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import Project, File

# Create your views here.
def load_code_editor(request, project_id=None):
    workspace_path = '/Users/aditya/Documents/Programming/Hackathon/PennApps/pennapps25/workspace-python/'
    
    # Clear existing files in workspace (except venv)
    if os.path.exists(workspace_path):
        items = os.listdir(workspace_path)
        print(f"Clearing workspace: {items}")
        for item in items:
            if item != 'venv':
                item_path = os.path.join(workspace_path, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    import shutil
                    shutil.rmtree(item_path)
    
    # Load project files if project_id is provided
    if project_id:
        try:
            project = get_object_or_404(Project, id=project_id)
            files = project.files.all()
            
            print(f"Loading project '{project.name}' with {files.count()} files")
            
            # Create all the project files
            for file_obj in files:
                file_path = os.path.join(workspace_path, file_obj.relative_path)
                
                # Create directory structure if it doesn't exist
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                # Write file content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(file_obj.content)
                    
                print(f"Created file: {file_obj.relative_path}")
                
        except Project.DoesNotExist:
            print(f"Project with ID {project_id} not found")
            # Create a default file if project doesn't exist
            default_content = """# Project not found
print("The requested project could not be loaded.")
print("This is a default Python file.")
"""
            with open(os.path.join(workspace_path, 'main.py'), 'w') as f:
                f.write(default_content)
    else:
        # Create default file when no project_id is provided
        default_content = """import time
print(f"Hello, it is {time.ctime()}")
"""
        with open(os.path.join(workspace_path, 'test.py'), 'w') as f:
            f.write(default_content)

    # Pass project information to template
    context = {}
    if project_id:
        try:
            project = Project.objects.get(id=project_id)
            context['current_project'] = project
        except Project.DoesNotExist:
            context['current_project'] = None
    
    return render(request, 'courses/editor.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def save_project(request):
    """
    Save project files from the code editor to the database
    Expected JSON payload:
    {
        "project_name": "MyProject",
        "project_description": "Optional description",
        "files": [
            {
                "relative_path": "main.py",
                "content": "print('Hello World')"
            },
            ...
        ]
    }
    """
    try:
        data = json.loads(request.body)
        project_name = data.get('project_name', 'Untitled Project')
        project_description = data.get('project_description', '')
        files_data = data.get('files', [])
        
        # Debug: Log the data structure
        print(f"DEBUG - Received data: {data}")
        print(f"DEBUG - Files data type: {type(files_data)}")
        print(f"DEBUG - Files data: {files_data}")
        
        # Create or get the project
        project, created = Project.objects.get_or_create(
            name=project_name,
            defaults={
                'description': project_description,
                'owner': request.user if request.user.is_authenticated else None
            }
        )
        
        # Update project description if it was provided
        if not created and project_description:
            project.description = project_description
            project.save()
        
        # Save or update files
        saved_files = []
        for file_data in files_data:
            # Ensure file_data is a dictionary
            if isinstance(file_data, dict):
                relative_path = file_data.get('relative_path', '')
                content = file_data.get('content', '')
            else:
                print(f"DEBUG - Unexpected file_data type: {type(file_data)}, value: {file_data}")
                continue
            
            if not relative_path:
                continue
                
            file_obj, file_created = File.objects.update_or_create(
                project=project,
                relative_path=relative_path,
                defaults={
                    'name': os.path.basename(relative_path),
                    'content': content
                }
            )
            saved_files.append({
                'path': relative_path,
                'created': file_created
            })
        
        return JsonResponse({
            'success': True,
            'message': f'Project "{project_name}" saved successfully',
            'project_id': project.id,
            'files_saved': len(saved_files),
            'files': saved_files
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error saving project: {str(e)}'
        }, status=500)

def get_workspace_files(request):
    """
    Get files from the workspace directory to save to the project
    """
    try:
        workspace_path = '/Users/aditya/Documents/Programming/Hackathon/PennApps/pennapps25/workspace-python/'
        files = []
        
        if os.path.exists(workspace_path):
            for root, dirs, filenames in os.walk(workspace_path):
                # Skip venv directory
                if 'venv' in dirs:
                    dirs.remove('venv')
                    
                for filename in filenames:
                    if filename.startswith('.'):
                        continue
                        
                    file_path = os.path.join(root, filename)
                    relative_path = os.path.relpath(file_path, workspace_path)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        files.append({
                            'relative_path': relative_path,
                            'content': content
                        })
                    except (UnicodeDecodeError, IOError):
                        # Skip binary files or files that can't be read
                        continue
        
        return JsonResponse({
            'success': True,
            'files': files
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error reading workspace files: {str(e)}'
        }, status=500)

def list_projects(request):
    """
    Display a list of all saved projects with links to load them in the editor
    """
    projects = Project.objects.all().order_by('-updated_at')
    return render(request, 'courses/project_list.html', {'projects': projects})