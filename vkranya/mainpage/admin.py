from django.contrib import admin
from .models import Subject, Specialty, DirectionSubject, AdmissionStats

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'name', 'faculty', 'url')
    search_fields = ('name', 'code', 'faculty', 'url')
    list_filter = ('faculty',)
    ordering = ('code',)


@admin.register(DirectionSubject)
class DirectionSubjectAdmin(admin.ModelAdmin):
    list_display = ('direction', 'subject', 'priority', 'min_points')
    list_filter = ('priority', 'direction__faculty', 'direction')
    search_fields = ('subject__name', 'direction__name')
    autocomplete_fields = ('direction', 'subject')  # Для удобного поиска


@admin.register(AdmissionStats)
class PassingScoreAdmin(admin.ModelAdmin):
    list_display = ('direction', 'year', 'score')
    list_filter = ('year', 'direction__faculty')
    search_fields = ('direction__name',)
    autocomplete_fields = ('direction',)