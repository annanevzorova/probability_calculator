/**
 * Утилиты для работы с DOM и безопасностью
 */
const Utils = {
    // Кэширование часто используемых элементов DOM для быстрого доступа
    elements: {
        form: document.getElementById('scores-form'),       // Главная форма ввода баллов
        results: document.getElementById('results'),       // Блок для вывода результатов
        loading: document.getElementById('loading-indicator'), // Индикатор загрузки
        error: document.getElementById('error-container'),  // Блок ошибок
        header: document.querySelector('.header')   // Блок шапки
    },

    // Константы приложения
    constants: {
        MIN_SCORE: 0,      // Минимально возможный балл ЕГЭ
        MAX_SCORE: 100,    // Максимально возможный балл ЕГЭ
        REQUIRED_SUBJECT: 'russian', // Обязательный для ввода предмет
        DEBOUNCE_DELAY: 500 // Задержка для устранения дребезга (не используется в текущей версии)
    },

    // Экранирование HTML-символов для защиты от XSS
    escapeHtml(unsafe) {
        if (!unsafe) return ''; // Если строка пустая, возвращаем пустую строку
        return unsafe
            .replace(/&/g, "&amp;")  // Заменяем & на &amp;
            .replace(/</g, "&lt;")    // < на &lt;
            .replace(/>/g, "&gt;")    // > на &gt;
            .replace(/"/g, "&quot;")  // " на &quot;
            .replace(/'/g, "&#039;"); // ' на &#039;
    },

    // Получение значения cookie по имени
    getCookie(name) {
        const cookies = document.cookie.split(';'); // Разбиваем все куки по разделителю ;
        for (let cookie of cookies) {
            const [cookieName, cookieValue] = cookie.trim().split('='); // Разделяем имя и значение
            if (cookieName === name) {
                return decodeURIComponent(cookieValue); // Декодируем значение (на случай %-кодирования)
            }
        }
        return null; // Если cookie не найдена
    }
};

/**
 * Сервис для отправки данных на сервер и получения результатов
 */
const ApiService = {
    // Отправка данных формы на сервер
    async calculateScores(formData) {
        try {
            // 1. Преобразуем объект в FormData (нужно для Django)
            const formDataObj = new FormData();
            for (const key in formData) {
                formDataObj.append(key, formData[key]); // Добавляем каждое поле
            }

            // 2. Получаем CSRF-токен из куков (защита от CSRF-атак)
            const csrfToken = Utils.getCookie('csrftoken');
            if (!csrfToken) {
                throw new Error('CSRF token not found'); // Если токена нет - ошибка
            }

            // 3. Отправляем POST-запрос на сервер
            const response = await fetch('/api/calculate/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken, // CSRF-токен в заголовке
                    'X-Requested-With': 'XMLHttpRequest' // Помечаем запрос как AJAX
                },
                body: formDataObj // Передаём данные формы
            });

            // 4. Проверяем статус ответа
            if (!response.ok) {
                const errorText = await response.text(); // Читаем текст ошибки
                throw new Error(`Ошибка сервера: ${response.status}. ${errorText}`);
            }

            // 5. Возвращаем JSON-ответ (например, {results: [...]})
            return await response.json();
        } catch (error) {
            console.error('API Error:', error); // Логируем ошибку в консоль
            throw error; // Пробрасываем её дальше
        }
    }
};

/**
 * Компонент для вывода результатов, ошибок и состояния загрузки
 */
const ResultsComponent = {
    // Шаблоны в виде строк HTML (для простоты, можно заменить на Handlebars/React)
    templates: {
        // Индикатор загрузки (спиннер + текст)
        loading: `
            <div class="loading">
                <div class="spinner"></div>
                <p>Идет расчет ваших результатов...</p>
            </div>
        `,

        // Шаблон ошибки (принимает сообщение)
        error: (message) => `
            <div class="error">
                <h3 class="error__title">Ошибка</h3>
                <p class="error__text">${Utils.escapeHtml(message)}</p>
                <p class="error__text">Попробуйте еще раз или обратитесь в поддержку.</p>
            </div>
        `,

        // Шаблон для случая, когда направлений нет
        noResults: `
            <div class="no-results">
                <h3 class="no-results__title">Результаты</h3>
                <p class="no-results__text">К сожалению, по вашим баллам не найдено подходящих специальностей.</p>
                <p class="no-results__text">Попробуйте изменить баллы или обратитесь в приемную комиссию.</p>
            </div>
        `,
        // Шаблон карточки направления (принимает объект specialty)
        specialtyCard: (specialty) => {
            // Определяем класс для вероятности (high/medium/low)
            const probabilityClass =
                specialty.probability >= 75 ? 'high' :
                    specialty.probability >= 50 ? 'medium' : 'low';

            // Генерируем HTML для карточки
            return `
        <div class="specialty-card">
          <div class="specialty-card__header">
            <a href="#">${Utils.escapeHtml(specialty.name)}</a>
            <span class="specialty-card__code">${Utils.escapeHtml(specialty.code)}</span>
          </div>
          <div class="specialty-card__faculty">${Utils.escapeHtml(specialty.faculty)}</div>
          <div class="specialty-card__details">
            <div class="detail">
              <span class="detail__label">Ваш балл:</span>
              <span class="detail__value">${specialty.total_score}</span>
            </div>
            <div class="detail">
              <span class="detail__label">Проходной балл:</span>
              <span class="detail__value">${specialty.passing_score}</span>
            </div>
          </div>
          <div class="probability probability-${probabilityClass}">
            Вероятность: ${specialty.probability}%
            <div class="probability__bar">
              <div style="width: ${specialty.probability}%" class="probability__bar-div"></div>
            </div>
          </div>
          <div class="subjects">
            <h5 class="subjects__header">Предметы:</h5>
            <ul class="subjects__ul">
              ${specialty.subjects.map(subj => `
                <li class="subjects__li">${Utils.escapeHtml(subj.name)} (мин. ${subj.min_points})
                  ${subj.is_required ? '<span class="required-badge">обязательный</span>' : ''}
                </li>
              `).join('')}
            </ul>
          </div>
        </div>
      `;
        }
    },

    // Показать индикатор загрузки
    showLoading() {
        Utils.elements.results.innerHTML = this.templates.loading;
    },

    // Показать ошибку
    showError(message) {
        Utils.elements.results.innerHTML = this.templates.error(message);
    },

    // Показать результаты (массив направлений)
    showResults(results) {
        if (!results || results.length === 0) {
            Utils.elements.results.innerHTML = this.templates.noResults;
            return;
        }

        // Сортируем по вероятности (от высокой к низкой)
        results.sort((a, b) => b.probability - a.probability);

        // Генерируем HTML для всех карточек
        let html = `
            <div class="result-section__container">
                <h3 class="result-section__title">Рекомендуемые направления</h3>
                ${results.length > 5 ? `<p class="result-section__notice">Показаны ${results.length} результатов</p>` : ''}
                <div class="specialties-list">
                    ${results.map(result => this.templates.specialtyCard(result)).join('')}
                </div>
            </div>
        `;

        // Вставляем в DOM
        Utils.elements.results.innerHTML = html;
    }
};

/**
 * Валидация формы
 */
const FormValidator = {
    // Проверка данных формы
    validateForm(formData) {
        // 1. Проверка обязательного предмета (русский язык)
        if (formData[Utils.constants.REQUIRED_SUBJECT] === 0) {
            throw new Error('Пожалуйста, введите баллы по русскому языку!');
        }

        // 2. Проверка, что все баллы в диапазоне 0-100
        const invalidSubjects = Object.entries(formData)
            .filter(([_, score]) => score < Utils.constants.MIN_SCORE || score > Utils.constants.MAX_SCORE)
            .map(([subject]) => subject);

        if (invalidSubjects.length > 0) {
            throw new Error(`Баллы должны быть между ${Utils.constants.MIN_SCORE} и ${Utils.constants.MAX_SCORE} для: ${invalidSubjects.join(', ')}`);
        }
    },

    // Валидация в реальном времени (подсветка невалидных полей)
    setupLiveValidation() {
        // Находим все числовые поля ввода
        const numberInputs = Array.from(Utils.elements.form.querySelectorAll('input[type="number"]'));

        // Для каждого поля добавляем обработчик
        numberInputs.forEach(input => {
            input.addEventListener('input', () => {
                const value = parseInt(input.value) || 0; // Приводим к числу (или 0)
                // Добавляем/удаляем класс 'invalid' в зависимости от валидности
                input.classList.toggle('invalid',
                    value < Utils.constants.MIN_SCORE ||
                    value > Utils.constants.MAX_SCORE
                );
            });
        });

    }
};

/**
 * Компонент для управления поведением header при скролле
 */
const HeaderComponent = {
    // Инициализация компонента
    init() {
        if (!Utils.elements.header) return; // Если header нет на странице, выходим
        
        let lastScrollTop = 0;
        // const headerHeight = Utils.elements.header.offsetHeight;
        const scrollOffset = 100; // Отступ для срабатывания фиксации
        
        // Добавляем отступ для body равный высоте header
        // document.body.style.paddingTop = `${headerHeight}px`;
        
        window.addEventListener('scroll', () => {
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            const isScrollingUp = scrollTop < lastScrollTop;
            const isAtTop = scrollTop <= 50;
            const isPastOffset = scrollTop > scrollOffset;
            
            // Фиксируем header если:
            // 1. Скроллим вниз и прошли отступ ИЛИ
            // 2. Скроллим вверх и header еще не зафиксирован И прошли отступ
            if ((!isScrollingUp && isPastOffset) || 
                (isScrollingUp && !this.isFixed() && isPastOffset)) {
                this.fixHeader();
            } 
            // Возвращаем обычное состояние только если в самом верху страницы
            else if (isAtTop) {
                this.unfixHeader();
            }
            
            lastScrollTop = scrollTop <= 0 ? 0 : scrollTop;
        });

        // Проверяем начальную позицию скролла
        if ((window.pageYOffset || document.documentElement.scrollTop) > scrollOffset) {
            this.fixHeader();
        }
    },

    // Проверка, зафиксирован ли header
    isFixed() {
        return Utils.elements.header.classList.contains('header--fixed');
    },
    
    // Фиксация header
    fixHeader() {
        if (Utils.elements.header.classList.contains('header--fixed')) return;
        
        Utils.elements.header.classList.add('header--fixed');
        // Можно добавить дополнительные действия при фиксации
    },
    
    // Возврат header в обычное состояние
    unfixHeader() {
        if (!Utils.elements.header.classList.contains('header--fixed')) return;
        
        Utils.elements.header.classList.remove('header--fixed');
        // Можно добавить дополнительные действия при возврате
    }
};

/**
 * Главный контроллер приложения
 */
const AppController = {
    // Обработчик отправки формы
    async handleFormSubmit(e) {
        e.preventDefault(); // Отменяем стандартную отправку формы

        try {
            // 1. Сбор данных формы
            const formData = this.getFormData();

            // 2. Проверяем валидность
            FormValidator.validateForm(formData);

            // 3. Показать индикатор загрузки
            ResultsComponent.showLoading();

            // 4. Отправляем данные на сервер
            const response = await ApiService.calculateScores(formData);

            // 5. Показываем результаты
            ResultsComponent.showResults(response.results);
        } catch (error) {
            console.error('Form Error:', error);
            ResultsComponent.showError(error.message); // Показываем ошибку пользователю
        }
    },

    // Сбор данных формы в объект
    getFormData() {
        const data = {};
        // Находим все поля ввода чисел
        const inputs = Utils.elements.form.querySelectorAll('input[type="number"]');
        inputs.forEach(input => {
            data[input.id] = parseInt(input.value) || 0; // Преобразуем в число (или 0)
        });
        return data;
    },

    /**
     * Настройка обработчика отправки формы
     */
    setupFormSubmit() {
        Utils.elements.form.addEventListener('submit', (e) => {
            this.handleFormSubmit(e);
        });
    },

    /**
     * Инициализация приложения
     */
    init() {
        FormValidator.setupLiveValidation(); // Включаем валидацию в реальном времени
        this.setupFormSubmit(); // Настраиваем отправку формы
        HeaderComponent.init();     // Инициализируем компонент header

    }

};

// Запуск приложения после загрузки DOM
document.addEventListener('DOMContentLoaded', () => AppController.init());