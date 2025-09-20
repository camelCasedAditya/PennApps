from django.contrib import admin
from django.urls import path, include
from .views import load_code_editor, save_project, get_workspace_files, list_projects

urlpatterns = [
    path("", list_projects, name="list_projects"),
    path("editor/", load_code_editor, name="load_code_editor"),
    path("editor/<int:project_id>/", load_code_editor, name="load_code_editor_with_project"),
    path("save_project/", save_project, name="save_project"),
    path("get_workspace_files/", get_workspace_files, name="get_workspace_files"),
]
