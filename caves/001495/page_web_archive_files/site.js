var _____WB$wombat$assign$function_____ = function(name) {return (self._wb_wombat && self._wb_wombat.local_init && self._wb_wombat.local_init(name)) || self[name]; };
if (!self.__WB_pmw) { self.__WB_pmw = function(obj) { this.__WB_source = obj; return this; } }
{
  let window = _____WB$wombat$assign$function_____("window");
  let self = _____WB$wombat$assign$function_____("self");
  let document = _____WB$wombat$assign$function_____("document");
  let location = _____WB$wombat$assign$function_____("location");
  //let top = _____WB$wombat$assign$function_____("top");
  let parent = _____WB$wombat$assign$function_____("parent");
  let frames = _____WB$wombat$assign$function_____("frames");
  let opener = _____WB$wombat$assign$function_____("opener");

﻿$.fn.extend({
    _setIcon: function (icon) {
        this.button({ icons: { primary: icon } });
        return this;
    },
    _setIconHideText: function (icon) {
        this.button({ icons: { primary: icon }, text: false });
        return this;
    },

    buttonEdit: function () { return this._setIcon("fa fa-pencil") },
    buttonBack: function () { return this._setIcon("fa fa-reply") },
    buttonBackToSearch: function () { return this._setIcon("fa fa-reply-all") },
    buttonClear: function () { return this._setIcon("fa fa-times") },
    buttonDetails: function () { return this._setIcon("fa fa-file-text-o") },
    buttonFileExport: function () { return this._setIcon("fa fa-download") },
    buttonGraphic: function () { return this._setIcon("fa fa-photo") },
    buttonSearch: function () { return this._setIcon("fa fa-search") },   
    buttonShowOnTheMap: function () { return this._setIcon("fa fa-globe") },
    buttonBibliography: function () { return this._setIcon("fa fa-book") },
    buttonCreate: function () { return this._setIcon("fa fa-plus") },
    buttonDictionary: function () { return this._setIcon("fa fa-list-alt") },
    buttonComments: function () { return this._setIcon("fa fa-comments") },
    buttonSave: function () { return this._setIcon("fa fa-save") },
    buttonAccept: function () { return this._setIcon("fa fa-check") },

    buttonMinus: function () { return this._setIconHideText("fa fa-minus") },
    buttonPlus: function () { return this._setIconHideText("fa fa-plus") },

    fontAwesome: function () {
        var pager = this.closest(".ui-jqgrid").find(".ui-pg-table");
        if (pager != null) {
            pager.find(".ui-pg-button>span.ui-icon-seek-first").removeClass("ui-icon ui-icon-seek-first").addClass("fa fa-step-backward fa-fw");
            pager.find(".ui-pg-button>span.ui-icon-seek-prev").removeClass("ui-icon ui-icon-seek-prev").addClass("fa fa-backward fa-fw");
            pager.find(".ui-pg-button>span.ui-icon-seek-next").removeClass("ui-icon ui-icon-seek-next").addClass("fa fa-forward fa-fw");
            pager.find(".ui-pg-button>span.ui-icon-seek-end").removeClass("ui-icon ui-icon-seek-end").addClass("fa fa-step-forward fa-fw");

            pager.find(".ui-pg-button>div>span.ui-icon-plus").removeClass("ui-icon ui-icon-plus").addClass("fa fa-plus fa-fw");
            pager.find(".ui-pg-button>div>span.ui-icon-pencil").removeClass("ui-icon ui-icon-pencil").addClass("fa fa-pencil fa-fw");
            pager.find(".ui-pg-button>div>span.ui-icon-trash").removeClass("ui-icon ui-icon-trash").addClass("fa fa-trash fa-fw");
        }

        var sortables = this.closest(".ui-jqgrid").find(".ui-jqgrid-htable .ui-jqgrid-labels .ui-jqgrid-sortable span.s-ico");
        if (sortables != null) {
            sortables.find(">span.ui-icon-triangle-1-n").removeClass("ui-icon ui-icon-triangle-1-n").addClass("fa fa-sort-asc fa-lg");
            sortables.find(">span.ui-icon-triangle-1-s").removeClass("ui-icon ui-icon-triangle-1-s").addClass("fa fa-sort-desc fa-lg");
        }
        return this;
    },

    xScroll: function () {
        var body = this.closest(".ui-jqgrid").find(".ui-jqgrid-bdiv");
        if (body != null) {
            body.css('overflow-x', 'auto');
        }
        return this;
    }
});

/*!
* ContextMenu - jQuery plugin for right-click context menus
*
* Author: Chris Domigan
* Contributors: Dan G. Switzer, II
* Parts of this plugin are inspired by Joern Zaefferer's Tooltip plugin
*
* Dual licensed under the MIT and GPL licenses:
*   http://www.opensource.org/licenses/mit-license.php
*   http://www.gnu.org/licenses/gpl.html
*
* Version: r2
* Date: 16 July 2007
*
* For documentation visit http://www.trendskitchens.co.nz/jquery/contextmenu/
*
*/

(function ($) {

    var menu, shadow, content, hash, currentTarget;
    var defaults = {
        menuStyle: {
            listStyle: 'none'
        },
        itemStyle: {
            display: 'block',
            border: '1px solid #ffffff'
        },
        itemHoverStyle: {
            border: '1px solid #999999'
        },
        eventPosX: 'pageX',
        eventPosY: 'pageY',
        shadow: true,
        onContextMenu: null,
        onShowMenu: null
    };

    $.fn.contextMenu = function (id, options) {
        if (!menu) {                                      // Create singleton menu
            menu = $('<div id="jqContextMenu"></div>')
               .hide()
               .css({ position: 'absolute', zIndex: '500' })
               .appendTo('body')
               .bind('click', function (e) {
                   e.stopPropagation();
               });
        }
        if (!shadow) {
            shadow = $('<div class="ui-corner-all"></div>')
                 .css({ backgroundColor: '#000', position: 'absolute', opacity: 0.2, zIndex: 499 })
                 .appendTo('body')
                 .hide();
        }
        hash = hash || [];
        hash.push({
            id: id,
            menuStyle: $.extend({}, defaults.menuStyle, options.menuStyle || {}),
            itemStyle: $.extend({}, defaults.itemStyle, options.itemStyle || {}),
            itemHoverStyle: $.extend({}, defaults.itemHoverStyle, options.itemHoverStyle || {}),
            bindings: options.bindings || {},
            shadow: options.shadow || options.shadow === false ? options.shadow : defaults.shadow,
            onContextMenu: options.onContextMenu || defaults.onContextMenu,
            onShowMenu: options.onShowMenu || defaults.onShowMenu,
            eventPosX: options.eventPosX || defaults.eventPosX,
            eventPosY: options.eventPosY || defaults.eventPosY
        });

        var index = hash.length - 1;
        $(this).bind('contextmenu', function (e) {
            // Check if onContextMenu() defined
            var bShowContext = (!!hash[index].onContextMenu) ? hash[index].onContextMenu(e) : true;
            currentTarget = e.target;
            if (bShowContext) {
                display(index, this, e);
                return false;
            }
        });
        return this;
    };

    function display(index, trigger, e) {
        var cur = hash[index];
        content = $('#' + cur.id).find('ul:first').clone(true);
        //content.css(cur.menuStyle).find('li').css(cur.itemStyle).hover(
        content.css(cur.menuStyle).find('li').addClass('ui-state-active').css(cur.itemStyle).hover(
      function () {
          //$(this).css(cur.itemHoverStyle);
          $(this).removeClass('ui-state-active').addClass('ui-state-default').css(cur.itemHoverStyle);
      },
      function () {
          //$(this).css(cur.itemStyle);
          $(this).removeClass('ui-state-default').addClass('ui-state-active').css(cur.itemStyle);
      }
    ).find('img').css({ verticalAlign: 'middle', paddingRight: '2px' });

        // Send the content to the menu
        menu.html(content);

        // if there's an onShowMenu, run it now -- must run after content has been added
        // if you try to alter the content variable before the menu.html(), IE6 has issues
        // updating the content
        if (!!cur.onShowMenu) menu = cur.onShowMenu(e, menu);

        $.each(cur.bindings, function (id, func) {
            $('#' + id, menu).bind('click', function () {
                hide();
                func(trigger, currentTarget);
            });
        });

        menu.css({ 'left': e[cur.eventPosX] - 1, 'top': e[cur.eventPosY] - 1 }).show();
        if (cur.shadow) shadow.css({ width: menu.width(), height: menu.height(), left: e.pageX + 2, top: e.pageY + 2 }).show();
        $(document).one('click', hide);
        menu.one("mouseleave", function () { hide(); });
    }

    function hide() {
        menu.hide();
        shadow.hide();
    }

    // Apply defaults
    $.contextMenu = {
        defaults: function (userDefaults) {
            $.each(userDefaults, function (i, val) {
                if (typeof val == 'object' && defaults[i]) {
                    $.extend(defaults[i], val);
                }
                else defaults[i] = val;
            });
        }
    };

})(jQuery);
/*!
* End of ContextMenu - jQuery plugin for right-click context menus
*/

$(function () {
    $('div.contextMenu').hide();
});
﻿

}
/*
     FILE ARCHIVED ON ﻿06:24:47 Dec 12, 2020﻿ AND RETRIEVED FROM THE
     INTERNET ARCHIVE ON ﻿13:10:56 Nov 07, 2024﻿.
     JAVASCRIPT APPENDED BY WAYBACK MACHINE, COPYRIGHT INTERNET ARCHIVE.

     ALL OTHER CONTENT MAY ALSO BE PROTECTED BY COPYRIGHT (17 U.S.C.
     SECTION 108(a)(3)).
*/
/*
﻿playback timings (ms):
﻿  ﻿captures_list﻿: ﻿0.485﻿
﻿  ﻿exclusion.robots﻿: ﻿0.016﻿
﻿  ﻿exclusion.robots.policy﻿: ﻿0.007﻿
﻿  ﻿esindex﻿: ﻿0.011﻿
﻿  ﻿cdx.remote﻿: ﻿23.957﻿
﻿  ﻿LoadShardBlock﻿: ﻿92.137﻿ (﻿3﻿)
﻿  ﻿PetaboxLoader3.datanode﻿: ﻿132.062﻿ (﻿5﻿)
﻿  ﻿load_resource﻿: ﻿393.781﻿ (﻿2﻿)
﻿  ﻿PetaboxLoader3.resolve﻿: ﻿273.648﻿ (﻿2﻿)
﻿*/