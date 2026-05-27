// Enhanced dark mode toggle functionality with animations
document.addEventListener("DOMContentLoaded", function () {
  const darkModeToggle = document.getElementById("darkModeToggle");
  const html = document.documentElement;

  // Check for saved dark mode preference or default to light mode
  const savedMode = localStorage.getItem("darkMode") || "light";
  if (savedMode === "dark") {
    html.classList.add("dark");
    updateToggleIcon(true);
  } else {
    html.classList.remove("dark");
    updateToggleIcon(false);
  }

  // Add click event listener with enhanced animations
  if (darkModeToggle) {
    darkModeToggle.addEventListener("click", function () {
      const isDarkMode = html.classList.contains("dark");

      // Add ripple effect
      addRippleEffect(darkModeToggle);

      // Add transition animation
      html.style.transition = "all 0.3s ease-in-out";

      if (isDarkMode) {
        html.classList.remove("dark");
        localStorage.setItem("darkMode", "light");
        updateToggleIcon(false);
        showModeNotification("Light Mode", "☀️");
      } else {
        html.classList.add("dark");
        localStorage.setItem("darkMode", "dark");
        updateToggleIcon(true);
        showModeNotification("Dark Mode", "🌙");
      }

      // Remove transition after animation
      setTimeout(() => {
        html.style.transition = "";
      }, 300);
    });
  }

  function updateToggleIcon(isDark) {
    if (darkModeToggle) {
      const iconSpan = darkModeToggle.querySelector("span");
      if (iconSpan) {
        // Add rotation animation
        iconSpan.style.transform = "rotate(180deg)";
        iconSpan.style.transition = "transform 0.3s ease-in-out";

        setTimeout(() => {
          if (isDark) {
            iconSpan.className = "text-yellow-400 text-lg";
            iconSpan.textContent = "☀️";
          } else {
            iconSpan.className = "text-gray-600 dark:text-yellow-400 text-lg";
            iconSpan.textContent = "🌙";
          }

          // Reset rotation
          iconSpan.style.transform = "rotate(0deg)";
        }, 150);
      }
    }
  }

  // Add ripple effect function
  function addRippleEffect(element) {
    const rect = element.getBoundingClientRect();
    const ripple = document.createElement("span");
    ripple.style.position = "absolute";
    ripple.style.borderRadius = "50%";
    ripple.style.background = "rgba(179, 156, 208, 0.6)";
    ripple.style.transform = "scale(0)";
    ripple.style.animation = "ripple 0.6s linear";
    ripple.style.left = "50%";
    ripple.style.top = "50%";
    ripple.style.width = "40px";
    ripple.style.height = "40px";
    ripple.style.marginLeft = "-20px";
    ripple.style.marginTop = "-20px";
    ripple.style.pointerEvents = "none";

    element.appendChild(ripple);

    setTimeout(() => {
      ripple.remove();
    }, 600);
  }

  // Show mode notification
  function showModeNotification(mode, icon) {
    const notification = document.createElement("div");
    notification.innerHTML = `
      <div class="flex items-center space-x-2">
        <span class="text-2xl">${icon}</span>
        <span class="font-medium">${mode} Activated</span>
      </div>
    `;
    notification.className =
      "fixed top-20 right-6 bg-white dark:bg-gray-800 text-gray-800 dark:text-white px-4 py-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-600 z-50 transition-all duration-300 transform translate-x-full";

    document.body.appendChild(notification);

    // Animate in
    setTimeout(() => {
      notification.style.transform = "translateX(0)";
    }, 100);

    // Animate out
    setTimeout(() => {
      notification.style.transform = "translateX(full)";
      setTimeout(() => {
        notification.remove();
      }, 300);
    }, 2000);
  }

  // Add CSS animation for ripple effect
  const style = document.createElement("style");
  style.textContent = `
    @keyframes ripple {
      0% {
        transform: scale(0);
        opacity: 1;
      }
      100% {
        transform: scale(4);
        opacity: 0;
      }
    }
  `;
  document.head.appendChild(style);

  // Add scroll-triggered animations
  function addScrollAnimations() {
    const observerOptions = {
      threshold: 0.1,
      rootMargin: "0px 0px -50px 0px",
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.style.opacity = "1";
          entry.target.style.transform = "translateY(0)";
        }
      });
    }, observerOptions);

    // Observe elements that should animate on scroll
    document
      .querySelectorAll(".card-hover, .list-item-animated")
      .forEach((el) => {
        el.style.opacity = "0";
        el.style.transform = "translateY(20px)";
        el.style.transition = "opacity 0.6s ease, transform 0.6s ease";
        observer.observe(el);
      });
  }

  // Initialize scroll animations
  setTimeout(addScrollAnimations, 500);
});
