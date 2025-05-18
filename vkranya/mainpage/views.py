from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q
from .models import Specialty, DirectionSubject, PassingScore
import json

def mainpage(request):
    """Рендеринг главной страницы с формой."""
    return render(request, 'mainpage/mainpage.html')

@require_POST
def calculate_admission(request):
    """
    Обработка POST-запроса с баллами ЕГЭ.
    Возвращает JSON с подходящими направлениями и вероятностью поступления.
    """
    try:
        # 1. Получаем данные из запроса
        data = json.loads(request.body)
        user_scores = {
            'математика': int(data.get('math', 0)),
            'русский язык': int(data.get('russian', 0)),
            'физика': int(data.get('physics', 0)),
            'информатика': int(data.get('informatics', 0)),
            # ... остальные предметы
        }

        # 2. Проверка на обязательные предметы (например, русский)
        if user_scores['русский язык'] == 0:
            return JsonResponse(
                {'error': 'Балл по русскому языку не может быть нулевым.'},
                status=400
            )

        # 3. Поиск подходящих направлений
        results = []
        specialties = Specialty.objects.prefetch_related('required_subjects')

        for specialty in specialties:
            # Проверяем обязательные предметы направления
            required_subjects = specialty.required_subjects.filter(priority=True)
            if not required_subjects.exists():
                continue

            # Проверка минимальных баллов по обязательным предметам
            meets_requirements = all(
                user_scores.get(subj.subject.name.lower(), 0) >= subj.min_points
                for subj in required_subjects
            )
            if not meets_requirements:
                continue

            # Сумма баллов по всем предметам направления
            total_score = sum(
                user_scores.get(subj.subject.name.lower(), 0)
                for subj in specialty.required_subjects.all()
            )

            # Получаем актуальный проходной балл (последний год)
            passing_score = PassingScore.objects.filter(
                direction=specialty
            ).order_by('-year').first()

            if not passing_score:
                continue

            # Расчёт вероятности (простая линейная модель)
            probability = min(
                100,
                max(0, int((total_score - passing_score.score) / passing_score.score * 50 + 50))
            )

            if probability >= 10:  # Исключаем варианты с шансом < 10%
                results.append({
                    'id': specialty.id,
                    'name': specialty.name,
                    'code': specialty.code,
                    'faculty': specialty.faculty,
                    'total_score': total_score,
                    'passing_score': passing_score.score,
                    'probability': probability,
                    'subjects': [
                        {
                            'name': subj.subject.name,
                            'min_points': subj.min_points,
                            'is_required': subj.priority
                        }
                        for subj in specialty.required_subjects.all()
                    ]
                })

        # Сортировка по убыванию вероятности
        results.sort(key=lambda x: x['probability'], reverse=True)

        return JsonResponse({'results': results})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Неверный формат данных.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)