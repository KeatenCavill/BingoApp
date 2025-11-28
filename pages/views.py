from django.shortcuts import render
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib import messages
from django.views import View
from django.views.generic import CreateView
from django.contrib.auth import login
from django.views.generic import (
    RedirectView,
    FormView,
    TemplateView,
    ListView,
    DetailView,
)

from .forms import CardCreateForm, SignUpForm
from .models import Card, Cell, SiteConfig

# Create your views here.

def build_grid(card: Card):
    size = card.board_size
    cells = card.cells.all()
    grid = [[None for _ in range(size)] for _ in range(size)]
    for cell in cells:
        grid[cell.row][cell.col] = cell
    return grid

class HomeRedirectView(RedirectView):
    pattern_name = "leaderboard"

    def get_redirect_url(self, *args, **kwargs):
        user = self.request.user
        if user.is_authenticated:
            if hasattr(user, "card"):
                return reverse_lazy("my_card")
            return reverse_lazy("create_card")
        return super().get_redirect_url(*args, **kwargs)
    
class CreateCardView(LoginRequiredMixin, FormView):
    template_name = "create_card.html"
    form_class = CardCreateForm
    success_url = reverse_lazy("my_card")

    def dispatch(self, request, *args, **kwargs):
        if hasattr(request.user, "card"):
            return redirect("my_card")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        config = SiteConfig.get_solo()
        kwargs["board_size"] = config.board_size
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context["form"]
        size = form.board_size
        center = size // 2

        # build a structure that the template can loop over
        grid = []
        for r in range(size):
            row = []
            for c in range(size):
                if r == center and c == center:
                    row.append({"is_free": True, "field": None})
                else:
                    field_name = f"cell_{r}_{c}"
                    row.append({"is_free": False, "field": form[field_name]})
            grid.append(row)

        context["board_size"] = size
        context["grid"] = grid
        return context

    def form_valid(self, form):
        user = self.request.user
        size = form.board_size
        center = size // 2

        card = Card.objects.create(user=user, board_size=size)

        for r in range(size):
            for c in range(size):
                if r == center and c == center:
                    Cell.objects.create(
                        card=card,
                        row=r,
                        col=c,
                        text="FREE",
                        is_free=True,
                        is_marked=True,
                    )
                else:
                    field_name = f"cell_{r}_{c}"
                    Cell.objects.create(
                        card=card,
                        row=r,
                        col=c,
                        text=form.cleaned_data[field_name],
                        is_free=False,
                    )

        return super().form_valid(form)

    
class MyCardView(LoginRequiredMixin, TemplateView):
    template_name = "my_card.html"

    def dispatch(self, request, *args, **kwargs):
        # If user has no card yet, send them to create one
        if not hasattr(request.user, "card"):
            return redirect("create_card")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        card = self.request.user.card
        context["card"] = card
        context["grid"] = build_grid(card)
        return context


class ToggleCellView(LoginRequiredMixin, View):
    """
    POST-only: mark a cell on the logged-in user's card.
    Once marked, it stays marked (no unmarking).
    """

    def post(self, request, *args, **kwargs):
        cell_id = kwargs.get("cell_id")
        cell = get_object_or_404(Cell, id=cell_id, card__user=request.user)

        # Optional: prevent changing the free center at all
        if not cell.is_marked and not cell.is_free:
            cell.is_marked = True
            cell.save()

        return redirect("my_card")

    # If someone does GET, just bounce them to their card
    def get(self, request, *args, **kwargs):
        return redirect("my_card")


class LeaderboardView(ListView):
    model = Card
    template_name = "leaderboard.html"
    context_object_name = "cards"

    def get_queryset(self):
        # Annotate with filled_count (excluding free)
        return (
            Card.objects.annotate(
                filled_count=Count(
                    "cells",
                    filter=Q(cells__is_marked=True, cells__is_free=False),
                    distinct=True,
                )
            )
            .select_related("user")
            .order_by("-filled_count", "user__username")
        )


class PublicCardView(DetailView):
    """
    Read-only card view for any player, looked up by their username.
    """
    model = Card
    template_name = "public_card.html"
    context_object_name = "card"

    def get_object(self, queryset=None):
        username = self.kwargs.get("username")
        return get_object_or_404(Card, user__username=username)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        card = context["card"]
        context["grid"] = build_grid(card)
        return context
    
class SignUpView(CreateView):
    template_name = "registration/signup.html"
    form_class = SignUpForm
    success_url = reverse_lazy("home")

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)  # log them in right away
        return redirect("home")

class SuperSettingsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "admin_controls.html"
    login_url = "login"

    def test_func(self):
        return self.request.user.is_superuser

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        return redirect("home")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config = SiteConfig.get_solo()
        context["config"] = config
        context["board_sizes"] = SiteConfig.BOARD_SIZES
        # NEW: all users who currently have a card
        context["cards_with_users"] = Card.objects.select_related("user").order_by("user__username")
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")
        config = SiteConfig.get_solo()

        if action == "reset_cards":
            Card.objects.all().delete()
            messages.success(request, "All cards have been reset. Players can create new cards now.")

        elif action == "change_size":
            try:
                new_size = int(request.POST.get("board_size"))
            except (TypeError, ValueError):
                new_size = config.board_size

            valid_sizes = [s for s, _ in SiteConfig.BOARD_SIZES]
            if new_size in valid_sizes:
                config.board_size = new_size
                config.save()
                messages.success(request, f"Board size set to {new_size} × {new_size}.")
            else:
                messages.error(request, "Invalid board size.")

        elif action == "reset_user":
            card_id = request.POST.get("user_card_id")
            if card_id:
                deleted, _ = Card.objects.filter(id=card_id).delete()
                if deleted:
                    messages.success(request, "Selected user's card has been reset.")
                else:
                    messages.error(request, "Could not find that card.")
            else:
                messages.error(request, "No user selected.")

        return redirect("admin_controls")