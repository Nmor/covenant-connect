document.addEventListener('DOMContentLoaded', function() {
    const html = document.documentElement;
    const themeToggle = document.getElementById('themeToggle');
    const themeIcon = document.getElementById('themeIcon');
    const footer = document.querySelector('.footer');

    function updateTheme(theme) {
        console.log('Theme toggle clicked:', {
            themeIcon: !!themeIcon,
            html: !!html,
            theme: html?.getAttribute('data-bs-theme')
        });

        // Update HTML theme
        if (html) {
            html.setAttribute('data-bs-theme', theme);
            localStorage.setItem('theme', theme);
        }

        // Update theme icon
        if (themeIcon && html) {
            themeIcon.className = theme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
        }

        // Update footer if it exists
        if (footer) {
            // Toggle background classes
            footer.classList.remove('bg-dark', 'bg-light');
            footer.classList.add(theme === 'dark' ? 'bg-dark' : 'bg-light');

            // Update footer text elements
            const footerTexts = footer.querySelectorAll('.footer-text');
            footerTexts.forEach(text => {
                if (text) {
                    text.classList.remove('text-light', 'text-dark');
                    text.classList.add(theme === 'dark' ? 'text-light' : 'text-dark');
                }
            });

            // Update footer headings
            const footerHeadings = footer.querySelectorAll('.footer-heading');
            footerHeadings.forEach(heading => {
                if (heading) {
                    heading.classList.remove('text-light', 'text-dark');
                    heading.classList.add(theme === 'dark' ? 'text-light' : 'text-dark');
                }
            });

            // Update footer links
            const footerLinks = footer.querySelectorAll('.footer-link');
            footerLinks.forEach(link => {
                if (link) {
                    link.classList.remove('text-light', 'text-dark');
                    link.classList.add(theme === 'dark' ? 'text-light' : 'text-dark');
                }
            });

            // Update footer divider
            const footerDivider = footer.querySelector('.footer-divider');
            if (footerDivider) {
                footerDivider.classList.remove('border-light', 'border-dark');
                footerDivider.classList.add(theme === 'dark' ? 'border-light' : 'border-dark');
            }
        }
    }

    // Initialize theme from localStorage or default to dark
    const savedTheme = localStorage.getItem('theme') || 'dark';
    updateTheme(savedTheme);

    // Add click handler for theme toggle if it exists
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            const currentTheme = html?.getAttribute('data-bs-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            updateTheme(newTheme);
        });
    }
});
