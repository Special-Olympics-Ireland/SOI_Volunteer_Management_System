from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'tasks'

router = DefaultRouter()
# Register ViewSets
router.register(r'tasks', views.TaskViewSet, basename='task')
router.register(r'completions', views.TaskCompletionViewSet, basename='taskcompletion')

urlpatterns = [
    # API endpoints - Direct router URLs
    path('', include(router.urls)),
    
    # Additional API views
    path('stats/', views.TaskStatsView.as_view(), name='task-stats'),
    
    # Task-specific endpoints
    path('tasks/<uuid:pk>/status/', views.TaskViewSet.as_view({'get': 'status', 'put': 'status', 'patch': 'status'}), name='task-status'),
    path('tasks/<uuid:pk>/stats/', views.TaskViewSet.as_view({'get': 'stats'}), name='task-detail-stats'),
    path('tasks/<uuid:pk>/assignments/', views.TaskViewSet.as_view({'get': 'assignments', 'post': 'assignments'}), name='task-assignments'),
    
    # Task filtering endpoints
    path('tasks/by-role/', views.TaskViewSet.as_view({'get': 'by_role'}), name='tasks-by-role'),
    path('tasks/by-event/', views.TaskViewSet.as_view({'get': 'by_event'}), name='tasks-by-event'),
    path('tasks/mandatory/', views.TaskViewSet.as_view({'get': 'mandatory'}), name='tasks-mandatory'),
    path('tasks/overdue/', views.TaskViewSet.as_view({'get': 'overdue'}), name='tasks-overdue'),
    path('tasks/high-priority/', views.TaskViewSet.as_view({'get': 'high_priority'}), name='tasks-high-priority'),
    
    # TaskCompletion-specific endpoints
    path('completions/<uuid:pk>/status/', views.TaskCompletionViewSet.as_view({'get': 'status', 'put': 'status', 'patch': 'status'}), name='completion-status'),
    path('completions/<uuid:pk>/workflow/', views.TaskCompletionViewSet.as_view({'post': 'workflow'}), name='completion-workflow'),
    path('completions/<uuid:pk>/progress/', views.TaskCompletionViewSet.as_view({'get': 'progress', 'put': 'progress', 'patch': 'progress'}), name='completion-progress'),
    path('completions/<uuid:pk>/start-work/', views.TaskCompletionViewSet.as_view({'post': 'start_work'}), name='completion-start-work'),
    path('completions/<uuid:pk>/verification/', views.TaskCompletionViewSet.as_view({'get': 'verification', 'put': 'verification', 'patch': 'verification'}), name='completion-verification'),
    
    # TaskCompletion bulk operations
    path('completions/bulk-operations/', views.TaskCompletionViewSet.as_view({'post': 'bulk_operations'}), name='completion-bulk-operations'),
    
    # TaskCompletion filtering endpoints
    path('completions/by-volunteer/', views.TaskCompletionViewSet.as_view({'get': 'by_volunteer'}), name='completions-by-volunteer'),
    path('completions/by-task/', views.TaskCompletionViewSet.as_view({'get': 'by_task'}), name='completions-by-task'),
    path('completions/pending-review/', views.TaskCompletionViewSet.as_view({'get': 'pending_review'}), name='completions-pending-review'),
    path('completions/pending-verification/', views.TaskCompletionViewSet.as_view({'get': 'pending_verification'}), name='completions-pending-verification'),
    path('completions/overdue/', views.TaskCompletionViewSet.as_view({'get': 'overdue'}), name='completions-overdue'),
] 