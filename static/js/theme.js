function updateTheme(theme) {
    document.addEventListener('DOMContentLoaded', function() {
        const html = document.documentElement;
        const footer = document.querySelector('.footer');
        
        if (!html || !footer) return; // Guard against null elements
        
        html.setAttribute('data-bs-theme', theme);
        localStorage.setItem('theme', theme);
        
        const themeIcon = document.getElementById('themeIcon');
        if (themeIcon) {
            themeIcon.className = theme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
        }
        
        footer.classList.toggle('bg-dark', theme === 'dark');
        footer.classList.toggle('bg-light', theme === 'light');
        
        const footerTexts = footer.querySelectorAll('.footer-text');
        footerTexts.forEach(text => {
            text.classList.toggle('text-light', theme === 'dark');
            text.classList.toggle('text-dark', theme === 'light');
        });
        
        const footerHeadings = footer.querySelectorAll('.footer-heading');
        footerHeadings.forEach(heading => {
            heading.classList.toggle('text-light', theme === 'dark');
            heading.classList.toggle('text-dark', theme === 'light');
        });
        
        const footerLinks = footer.querySelectorAll('.footer-link');
        footerLinks.forEach(link => {
            link.classList.toggle('text-light', theme === 'dark');
            link.classList.toggle('text-dark', theme === 'light');
        });
        
        const footerDivider = footer.querySelector('.footer-divider');
        if (footerDivider) {
            footerDivider.classList.toggle('border-light', theme === 'dark');
            footerDivider.classList.toggle('border-dark', theme === 'light');
        }
    });
}

document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        const savedTheme = localStorage.getItem('theme') || 'dark';
        updateTheme(savedTheme);
        
        themeToggle.addEventListener('click', function() {
            const currentTheme = document.documentElement.getAttribute('data-bs-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            updateTheme(newTheme);
        });
    }
});
