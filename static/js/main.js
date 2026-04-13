// InvestIQ — Main JS
document.addEventListener('DOMContentLoaded', () => {
    // Smooth page entrance
    document.body.style.opacity = '0';
    document.body.style.transition = 'opacity 0.4s ease';
    requestAnimationFrame(() => {
        document.body.style.opacity = '1';
    });

    // Animate elements with data-animate
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.feature-card, .section-card').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
        observer.observe(el);
    });

    // Feature card stagger
    document.querySelectorAll('.feature-card').forEach((el, i) => {
        el.style.transitionDelay = `${i * 0.1}s`;
    });
});

// Custom event to handle animated elements
document.addEventListener('animationend', (e) => {
    if (e.target.classList.contains('animate-in')) {
        e.target.style.opacity = '';
        e.target.style.transform = '';
    }
});

// Helper to add animate-in styles
const style = document.createElement('style');
style.textContent = `.animate-in { opacity: 1 !important; transform: translateY(0) !important; }`;
document.head.appendChild(style);