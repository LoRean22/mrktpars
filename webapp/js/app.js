const container = document.getElementById("page-container");
const buttons = document.querySelectorAll(".bottom-nav button");

const API_BASE = "http://46.253.143.163:8000";

let subscriptionData = null;

// --------------------
// ИНИЦИАЛИЗАЦИЯ ПОЛЬЗОВАТЕЛЯ
// --------------------123

async function initUser() {
  const user = window.tgUser;

  if (!user) {
    console.log("Нет tgUser");
    return;
  }

  try {
    const response = await fetch(`${API_BASE}/users/init`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        tg_id: user.id,
        username: user.username,
      }),
    });

    if (!response.ok) {
      console.error("Ошибка backend:", response.status);
      return;
    }

    subscriptionData = await response.json();
    console.log("Данные подписки:", subscriptionData);
  } catch (err) {
    console.error("Ошибка соединения:", err);
  }
}

// --------------------
// РЕНДЕР СТРАНИЦ
// --------------------

function renderPage(page) {
  if (page === "info") {
    container.innerHTML = `
      <h1>MRKTPARS</h1>
      <div class="card">
        <div>
          <strong>Авито Парсер</strong>
          <span>Следи за выгодными объявлениями</span>
        </div>
      </div>
    `;
  }

  if (page === "subscriptions") {
    container.innerHTML = `
      <h1>Подписки</h1>
      <div class="card clickable">
        <div>
          <strong>Добавить поиск</strong>
          <span>Создай новый мониторинг</span>
        </div>
      </div>
    `;
  }

  if (page === "profile") {
    const user = window.tgUser;

    container.innerHTML = `
      <h1>Профиль</h1>
      ${
        user
          ? `
          <div class="card profile-card">
            <div class="username">
              @${user.username || "без username"}
            </div>
            <div class="tg-id">
              Telegram ID: ${user.id}
            </div>
          </div>

          <div class="card profile-card">
            <div class="subscription-title">
              Текущая подписка
            </div>
            <div class="subscription-value">
              ${
                subscriptionData && subscriptionData.subscription_type
                  ? subscriptionData.subscription_type.toUpperCase()
                  : "Нет активной подписки"
              }
            </div>
              ${
                subscriptionData && subscriptionData.subscription_expires
                  ? `<div class="hint">
                      Действует до: ${new Date(
                        subscriptionData.subscription_expires
                      ).toLocaleDateString()}
                    </div>`
                  : ""
              }
          </div>
          `
          : `
          <div class="card">
            <strong>Нет данных пользователя</strong>
          </div>
          `
      }
    `;
  }
}

// --------------------
// НАВИГАЦИЯ
// --------------------

buttons.forEach((btn) => {
  btn.addEventListener("click", () => {
    buttons.forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");

    const page = btn.dataset.page;
    renderPage(page);
  });
});

// --------------------
// ЗАПУСК
// --------------------

(async () => {
  await initUser();
  renderPage("info");
})();
