"""Views for AstroPulse.

Server-rendered templates only. No JavaScript yet.
Every page inherits the footer: 'Decision support, not a diagnosis.'
"""
from django.shortcuts import render


def home(request):
    """Home page placeholder: confirms the Django project is running."""
    return render(request, "core/home.html")
