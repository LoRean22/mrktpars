const tg = window.Telegram.WebApp;

tg.ready();
tg.expand();

window.tg = tg;

if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
    window.tgUser = tg.initDataUnsafe.user;
    console.log("Telegram user:", window.tgUser);
} else {
    console.warn("Нет Telegram user");
}

console.log("Telegram object:", window.Telegram);
console.log("InitDataUnsafe:", window.Telegram?.WebApp?.initDataUnsafe);
console.log("tgUser:", window.tgUser);
