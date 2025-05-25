function toggleLanguageDropdown() {
    const dropdown = document.getElementById('languageDropdown');
    dropdown.classList.toggle('show');
}

function changeLanguage(lang, curr) {
    if (lang !== curr) {
        const url = new URL(window.location.href);
        url.searchParams.set('lang', lang);
        window.location.href = url.toString();
    }
}

// Close the dropdown if clicked outside
window.onclick = function(event) {
    if (!event.target.matches('.language-button') && !event.target.matches('.language-button span')) {
        const dropdowns = document.getElementsByClassName("language-dropdown");
        for (let i = 0; i < dropdowns.length; i++) {
            const openDropdown = dropdowns[i];
            if (openDropdown.classList.contains('show')) {
                openDropdown.classList.remove('show');
            }
        }
    }
}