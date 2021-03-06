
function Crawler (options) {
    if (this === window) 
        return new Crawler(options);

    var defaults = {
        delay: 100,
        done_after_stop: true
    };
    var opts = $.extend(true, {}, defaults);
        opts = $.extend(true, opts, options || {});

    var that = this;
    var started = false;
    var done = false;
    var stopped = false;
    var duns_queue = [];
    var name_queue = [];
    var duns_results = [];
    var name_results = [];
    var link_results = [];

    var recv_results = function (response, query_queue, past_results, result_type) {
        if (done) {
            if (opts.done_after_stop) {
                that.finish();
            }
            return;
        }

        var a_node = response.query.toUpperCase();
        for (var idx = 0; idx < response.results.length; idx++) {
            var b_node = response.results[idx].toUpperCase();
            if (past_results.indexOf(b_node) == -1) {
                query_queue.push(b_node);
                past_results.push(b_node);
                $(that).trigger('noderesult', [b_node, result_type]);
            }
            var a_to_b = [a_node, b_node];
            var b_to_a = [b_node, a_node];
            var is_new_link = (    (link_results.indexOf(a_to_b) == -1) 
                                && (link_results.indexOf(b_to_a) == -1) );
            if (is_new_link == true) {
                link_results.push(a_to_b);
                $(that).trigger('linkresult', [a_to_b, result_type]);
            }
        }
        if (!stopped && !done) {
            process_queues();
        }
    };

    var recv_names = function (data, text_status, xhr) {
        recv_results(data, name_queue, name_results, 'name');
    };

    var recv_duns = function (data, text_status, xhr) {
        recv_results(data, duns_queue, duns_results, 'duns');
    };

    var search_by_duns = function (duns) {
        $.ajax("duns/" + duns,
                { data: "q=",
                  success: recv_names });
    };

    var search_by_name = function (name) {
        $.ajax("duns/" + encodeURIComponent(name),
                { data: "q=",
                  success: recv_duns });
    };

    var process_queues = function () {
        if (name_queue.length > 0) {
            var name = name_queue.shift();
            setTimeout(function(){ search_by_name(name); },
                       opts.delay);
        } else if (duns_queue.length > 0) {
            var duns = duns_queue.shift();
            setTimeout(function(){ search_by_duns(duns); },
                       opts.delay);
        } else {
            that.finish();
        }
    };

    this.finish = function () {
        done = true;
        $(that).trigger('done', duns_results, name_results);
    };

    this.stop = function () {
        stopped = true;
        $(that).trigger('stop');
    };

    this.resume = function () {
        if (done) {
            throw 'Crawler previously completed the search.';
        }

        stopped = false;
        started = true;
        process_queues();
    };

    this.start = function (seed, seed_type) {
        if (started || stopped || done ) {
            throw "Crawler objects are not restartable. Did you mean resume()?";
            return;
        }

        if (seed_type.toLowerCase() == 'duns') {
            duns_queue.push(seed);
            started = true;
            process_queues();
        } else if (seed_type.toLowerCase() == 'name') {
            name_queue.push(seed);
            started = true;
            process_queues();
        } else {
            throw ('Invalid crawler seed type: ' + seed_type);
        }
    };

    this.is_running = function () { return started && !done && !stopped; };
    this.is_started = function () { return started; };
    this.is_done = function () { return started && done; };
    this.name_queue_length = function () { return name_queue.length; };
    this.duns_queue_length = function () { return duns_queue.length; };

    return that;
}

