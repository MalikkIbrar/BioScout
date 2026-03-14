from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ObservationViewSet
from .ai_views import identify_and_save, species_qa

router = DefaultRouter()
router.register(r'observations', ObservationViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('identify/', identify_and_save, name='identify_and_save'),
    path('species_qa/', species_qa, name='species_qa'),

]
