from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Card(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='card')
    created_at = models.DateTimeField(auto_now_add=True)
    board_size = models.PositiveSmallIntegerField(default = 5)

    def __str__(self):
        return f"{self.user.username}'s card"
    
    @property
    def marked_count(self):
        return self.cells.filter(is_marked=True, is_free=False).count()
    
class Cell(models.Model):
    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name="cells")
    row = models.PositiveSmallIntegerField()
    col = models.PositiveSmallIntegerField()
    text = models.CharField(max_length = 100, blank=True)
    is_free = models.BooleanField(default=False)
    is_marked = models.BooleanField(default=False)

    class Meta:
        unique_together =("card", "row", "col")
        ordering = ["row", "col"]

    def __str__(self):
        return f"{self.card.user.username} ({self.row}, {self.col})"
    
class SiteConfig(models.Model):
    BOARD_SIZES = [
        (5, "5 x 5"),
        (7, "7 x 7"),
        (9, "9 x 9"),
    ]

    board_size = models.PositiveSmallIntegerField(
        choices=BOARD_SIZES,
        default=5,
    )

    def __str__(self):
        return "Bingo Settings"

    @classmethod
    def get_solo(cls):
        # always use the same row (id=1)
        obj, created = cls.objects.get_or_create(pk=1)
        return obj