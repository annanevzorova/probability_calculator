from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import Specialty, AdmissionStats
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

        for specialty in specialties:
            required_subjects = specialty.required_subjects.filter(priority=True)
            optional_subjects = specialty.required_subjects.filter(priority=False)
            if not required_subjects.exists():
                continue

            # Проверка обязательных предметов
            valid = True
            total_score = 0

            for subj in required_subjects:
                subject_name = subj.subject.name.lower()
                user_score = user_scores.get(subject_name, 0)

                if user_score < subj.min_points:
                    valid = False
                    break

                total_score += user_score

            if not valid:
                continue

            best_optional_score = 0
            best_optional_name = None
            has_valid_optional = False

            # Если есть предметы по выбору, пробуем найти лучший
            if optional_subjects.exists():
                for subj in optional_subjects:
                    subject_name = subj.subject.name.lower()
                    user_score = user_scores.get(subject_name, 0)

                    if user_score >= subj.min_points:
                        has_valid_optional = True
                        if user_score > best_optional_score:
                            best_optional_score = user_score
                            best_optional_name = subj.subject.name

                        # Если предметы по выбору есть, но ни один не подходит - пропускаем направление
                if not has_valid_optional:
                    continue
                # Добавляем лучший предмет по выбору, если нашли
                if best_optional_score > 0:
                    total_score += best_optional_score

            # Получаем средний балл
            admission_stats = AdmissionStats.objects.filter(
                direction=specialty
            ).order_by('-year').first()

            if not admission_stats:
                continue

            # Расчет вероятности (более точная формула)
            average_score = admission_stats.score

            difference = 1 - (total_score/average_score)

            if difference <= -0.6:
                probability = "Высокая"
            elif -0.6 < difference <= -0.3:
                probability = "Выше среднего"
            elif -0.3 < difference <= 0:
                probability = "Средняя"
            elif 0 < difference <= 0.3:
                probability = "Ниже среднего"
            else:
                probability = "Низкая"

            subjects_info = []
            for subj in specialty.required_subjects.all():
                subject_name = subj.subject.name.lower()
                is_selected = (not subj.priority and
                               subj.subject.name == best_optional_name)

                subjects_info.append({
                    'name': subj.subject.name,
                    'min_points': subj.min_points,
                    'is_required': subj.priority,
                    'user_score': user_scores.get(subject_name, 0),
                    'is_selected': is_selected
                })

            results.append({
                'id': specialty.id,
                'name': specialty.name,
                'code': specialty.code,
                'faculty': specialty.faculty,
                'total_score': total_score,
                'passing_score': admission_stats.score,
                'places': admission_stats.number_of_places,
                'probability': probability,
                'subjects': subjects_info,
                'used_optional_subject': best_optional_name,
                'url': specialty.url
            })

        # Сортировка и ограничение результатов
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