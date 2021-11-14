/*!
 * Start Bootstrap - Creative Bootstrap Theme (http://startbootstrap.com)
 * Code licensed under the Apache License v2.0.
 * For details, see http://www.apache.org/licenses/LICENSE-2.0.
 */

(function($) {
    "use strict"; // Start of use strict

    // jQuery for page scrolling feature - requires jQuery Easing plugin
    $('a.page-scroll').bind('click', function(event) {
        var $anchor = $(this);
        $('html, body').stop().animate({
            scrollTop: ($($anchor.attr('href')).offset().top - 50)
        }, 1250, 'easeInOutExpo');
        event.preventDefault();
    });

    // Highlight the top nav as scrolling occurs
    $('body').scrollspy({
        target: '.navbar-fixed-top',
        offset: 51
    })

    // Closes the Responsive Menu on Menu Item Click
    $('.navbar-collapse ul li a').click(function() {
        $('.navbar-toggle:visible').click();
    });

    // Fit Text Plugin for Main Header
    $("h1").fitText(
        0.6, {
            minFontSize: '35px',
            maxFontSize: '110px'
        }
    );

    // Offset for Main Navigation
    $('#mainNav').affix({
        offset: {
            top: 100
        }
    })

    // Sliders
    var sliders = [];
    $('.single-slider').each(function() {
        sliders.push(
            tns({
                container: this,
                controls: false,
                navPosition: 'bottom',
                loop: false,
                mouseDrag: true,
                items: 1,
            })
        );
    });

    // Media query for sliders
    function collapseSlider(x) {
        var src = $('.cards-indicators .active').attr('data-slide-to');
        if (x.matches) {  // big
            $('#cards').carousel(src % 2 ? 1 : 0);
            $('.cards-indicators .btn').each(function(i) {
                $(this).attr('data-slide-to', i);
            });
        } else {  // small
            sliders[src % 2].goTo(0);
            $('#cards').carousel(src % 2 ? 3 : 2);
            $('.cards-indicators .btn').each(function(i) {
                $(this).attr('data-slide-to', i+2);
            });
        }
    }

    var cond = window.matchMedia('(min-width: 768px)');
    collapseSlider(cond);
    cond.addListener(collapseSlider);

    // Source toggle
    $('#get-started .btn').click(function() {
        $('#get-started .btn').removeClass('active');
        $(this).addClass('active');
        setTimeout(function() {  // animation off screen
            sliders.forEach(function(slider) {
                slider.goTo(0);
            });
        }, 1000);
    });

    // Modal preview
    $('.narrow .card img').removeClass('img-pop');  // no modal on mobile
    $('.img-pop').click(function() {
        $('.img-preview').attr('src', $(this).attr('src'));
        $('#img-modal').modal('show');
    });

    // Initialize WOW.js Scrolling Animations
    new WOW().init();

})(jQuery); // End of use strict