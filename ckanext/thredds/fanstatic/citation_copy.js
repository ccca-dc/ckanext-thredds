ckan.module('citation_copy', function ($) {
  return {
      /* options object can be extended using data-module-* attributes */
      initialize: function () {
        var self = this;
        $.proxyAll(this, /_on/);
        // Add click event
        document.getElementById('copy-button').addEventListener('click', function(e){
          self._CopyToClipboard("citation-text");
        });
      },

      _CopyToClipboard: function(containerid) {
      if (document.selection) { 
          var range = document.body.createTextRange();
          range.moveToElementText(document.getElementById(containerid));
          range.select().createTextRange();
          document.execCommand("Copy"); 
      
      } else if (window.getSelection) {
          var range = document.createRange();
           range.selectNode(document.getElementById(containerid));
           window.getSelection().addRange(range);
           document.execCommand("Copy");

           // Remove selection
           if (window.getSelection) {
             if (window.getSelection().empty) {  // Chrome
               window.getSelection().empty();
             } else if (window.getSelection().removeAllRanges) {  // Firefox
               window.getSelection().removeAllRanges();
             }
           } else if (document.selection) {  // IE?
             document.selection.empty();
           }

           alert("Citation copied to Clipboard") 
      }}
      
  };
});

