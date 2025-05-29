from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db.models import Q
from .models import Specialty, DirectionSubject, PassingScore
import json

@ensure_csrf_cookie
def mainpage(request):
    """Рендеринг главной страницы с формой и CSRF-токеном"""
    return render(request, 'mainpage/mainpage.html')

@require_POST
def calculate_admission(request):
    """
    Обработка POST-запроса с баллами ЕГЭ.
    Возвращает JSON с подходящими направлениями и вероятностью поступления.
    """
    try:
        # 1. Получение данных из запроса (разные форматы)
        if request.content_type == 'application/json':
            data = json.loads(request.body)  # Если данные в JSON
        else:
            data = request.POST.dict()  # Если обычная форма

        # 2. Преобразование ключей в нижний регистр для унификации
        user_scores = {
            'математика': int(data.get('math', 0)),
            'русский язык': int(data.get('russian', 0)),
            'физика': int(data.get('physics', 0)),
            'информатика': int(data.get('informatics', 0)),
            'химия': int(data.get('chemistry', 0)),
            'биология': int(data.get('biology', 0)),
            'обществознание': int(data.get('social', 0)),
            'история': int(data.get('history', 0)),
            'английский язык': int(data.get('english', 0)),
            'литература': int(data.get('literature', 0))
        }

        # 3. Валидация данных
        if not all(0 <= score <= 100 for score in user_scores.values()):
            return JsonResponse(
                {'error': 'Все баллы должны быть в диапазоне от 0 до 100'},
                status=400
            )

        if user_scores['русский язык'] == 0:
            return JsonResponse(
                {'error': 'Балл по русскому языку не может быть нулевым'},
                status=400
            )

        # 4. Поиск подходящих направлений
        results = []
        specialties = Specialty.objects.prefetch_related(
            'required_subjects__subject'
        ).all()

        MAX_POSSIBLE_SCORE = 315  # Максимально возможный суммарный балл

        for specialty in specialties:
            required_subjects = specialty.required_subjects.filter(priority=True)
            if not required_subjects.exists():
                continue

            # Проверка обязательных предметов
            valid = True
            total_score = 0

            for subj in specialty.required_subjects.all():
                subject_name = subj.subject.name.lower()
                user_score = user_scores.get(subject_name, 0)

                if subj.priority and user_score < subj.min_points:
                    valid = False
                    break

                total_score += user_score

            if not valid:
                continue

            # Получаем проходной балл
            passing_score = PassingScore.objects.filter(
                direction=specialty
            ).order_by('-year').first()

            if not passing_score:
                continue

            # Расчет вероятности (более точная формула)
            last_year_score = passing_score.score
            probability = 0.0

            if total_score >= last_year_score:
                probability = 0.5 + 0.5 * (total_score - last_year_score) / (MAX_POSSIBLE_SCORE - last_year_score)
            else:
                probability = 0.5 * (total_score / last_year_score)

            # Ограничиваем вероятность между 0 и 1 и преобразуем в проценты
            probability_percent = round(min(max(probability, 0), 1) * 100)

            results.append({
                'id': specialty.id,
                'name': specialty.name,
                'code': specialty.code,
                'faculty': specialty.faculty,
                'total_score': total_score,
                'passing_score': passing_score.score,
                'probability': probability_percent,
                'subjects': [
                    {
                        'name': subj.subject.name,
                        'min_points': subj.min_points,
                        'is_required': subj.priority
                    }
                    for subj in specialty.required_subjects.all()
                ]
            })

        # Сортировка и ограничение результатов
        results.sort(key=lambda x: (-x['probability'], -x['total_score']))
        results = results[:20]  # Лимит результатов

        return JsonResponse({
            'results': results,
            'count': len(results)
        })

    except json.JSONDecodeError:
        return JsonResponse(
            {'error': 'Неверный формат данных. Отправьте JSON или форму'},
            status=400
        )
    except Exception as e:
        return JsonResponse(
            {'error': f'Внутренняя ошибка сервера: {str(e)}'},
            status=500
        )