from django.db import models

# Модель для хранения предметов ЕГЭ
class Subject(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название предмета")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Предмет"
        verbose_name_plural = "Предметы"


# Модель для хранения специальностей/направлений
class Specialty(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название направления")
    code = models.CharField(max_length=50, verbose_name="Код направления")
    faculty = models.CharField(max_length=255, verbose_name="Факультет")
    url = models.URLField(
        max_length=500,
        verbose_name="URL страницы специальности",
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.code} - {self.name}"

    class Meta:
        verbose_name = "Направление"
        verbose_name_plural = "Направления"


# Модель для связи предметов и направлений с указанием приоритета и минимальных баллов
class DirectionSubject(models.Model):
    direction = models.ForeignKey(
        Specialty,
        on_delete=models.CASCADE,
        verbose_name="Направление",
        related_name='required_subjects'
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        verbose_name="Предмет"
    )
    priority = models.BooleanField(
        default=False,
        verbose_name="Обязательный предмет",
        help_text="Отметьте для обязательных предметов (например, математика и русский)"
    )
    min_points = models.PositiveSmallIntegerField(
        verbose_name="Минимальный балл"
    )

    def __str__(self):
        required = " (обязательный)" if self.priority else ""
        return f"{self.direction}: {self.subject}{required}, мин. {self.min_points}"

    class Meta:
        verbose_name = "Предмет направления"
        verbose_name_plural = "Предметы направлений"
        unique_together = ('direction', 'subject')


# Модель для хранения проходных баллов по годам
class AdmissionStats(models.Model):
    direction = models.ForeignKey(
        Specialty,
        on_delete=models.CASCADE,
        verbose_name="Направление",
        related_name='admission_stats'
    )
    year = models.PositiveSmallIntegerField(verbose_name="Год")
    score = models.PositiveSmallIntegerField(verbose_name="Средний балл")
    number_of_places = models.PositiveSmallIntegerField(verbose_name="Количество мест")

    def __str__(self):
        return f"{self.direction} ({self.year}): {self.score}"

    class Meta:
        verbose_name = "Средний балл"
        verbose_name_plural = "Средние баллы"
        # Уникальность комбинации направления и года
        unique_together = ('direction', 'year')