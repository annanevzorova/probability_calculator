document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('scores-form');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(form);
        const scores = Object.fromEntries(formData.entries());

        try {
            const response = await fetch('/api/calculate/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                },
                body: JSON.stringify(scores),
            });

            const data = await response.json();
            if (data.error) throw new Error(data.error);
            displayResults(data.results);
        } catch (error) {
            console.error('Ошибка:', error);
        }
    });
});

function displayResults(results) {
    const container = document.getElementById('results');
    // ... логика рендеринга результатов (аналогично вашему старому JS)
}