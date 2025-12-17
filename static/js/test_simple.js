console.log("TEST_SIMPLE.JS is loading!");
document.addEventListener('DOMContentLoaded', function() {
    console.log("TEST_SIMPLE.JS DOM is ready!");
    var form = document.getElementById('mining-calculator-form');
    console.log("TEST_SIMPLE.JS found form:", form);
    
    if(form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            console.log("TEST_SIMPLE.JS form submitted!");
            alert('Form submitted! Check console for details.');
        });
    }
});
