var gulp = require('gulp'),
    uglify = require('gulp-uglify'),
    rename = require('gulp-rename'),
    source = require('vinyl-source-stream'),
    concat = require('gulp-concat'),
    browserify = require('browserify'),
    reactify = require('reactify'),
    streamify = require('gulp-streamify'),
    underscorify = require('node-underscorify').transform({
        templateSettings: {
            variable: 'data'
        }
    }),
    less = require('gulp-less'),
    // sourcemaps = require('gulp-sourcemaps'),
    replace = require('gulp-replace'),
    livereload = require('gulp-livereload'),
    es = require('event-stream');

// base paths
var src_path = 'dokomoforms/static/src',
    dist_path = 'dokomoforms/static/dist',
    common_src_path = src_path + '/common',
    admin_src_path = src_path + '/admin',
    survey_src_path = src_path + '/survey',
    admin_dist_path = dist_path + '/admin',
    survey_dist_path = dist_path + '/survey',
    node_modules_path = 'node_modules';

// explicit file/dir paths
var path = {

    // COMMON PATH NAMES
    JS_BUILD_FILENAME: 'build.js',
    JS_MINIFIED_BUILD_FILENAME: 'build.min.js',
    COMMON_IMG_SRC: common_src_path + '/img/**/*',


    //---------------------
    // SURVEY ASSET PATHS


    SURVEY_LESS_SRC: survey_src_path + '/less/*.less',
    SURVEY_LESS_ENTRY_POINT: survey_src_path + '/less/survey.less',
    SURVEY_CSS_DIST: survey_dist_path + '/css',
    // SURVEY_CSS_BUILD: survey_dist_path + '/css/survey/*.css',

    SURVEY_JS_VENDOR_SRC: [
        node_modules_path + '/jquery/dist/jquery.js',
        node_modules_path + '/bootstrap/dist/js/bootstrap.js',
        node_modules_path + '/lodash/lodash.js',
        node_modules_path + '/moment/min/moment.min.js',
        node_modules_path + '/react/dist/react.js'
    ],
    SURVEY_JS_APP_SRC: survey_src_path + '/js/**/*.js',
    SURVEY_JS_ENTRY_POINT: survey_src_path + '/js/main.js',
    SURVEY_JS_DIST: survey_dist_path + '/js',

    SURVEY_IMG_SRC: survey_src_path + '/img/**/*',
    SURVEY_IMG_DIST: survey_dist_path + '/img',

    SURVEY_FONT_SRC: [
        node_modules_path + '/ratchet/fonts/*'
    ],
    SURVEY_FONT_DIST: survey_dist_path + '/fonts',

    APP_CACHE_SRC: survey_src_path + '/cache.appcache',
    APP_CACHE_DIST: survey_dist_path + '/',


    //---------------------
    // ADMIN ASSET PATHS


    ADMIN_LESS_SRC: admin_src_path + '/less/*.less',
    ADMIN_LESS_ENTRY_POINT: admin_src_path + '/less/admin.less',
    ADMIN_CSS_DIST: admin_dist_path + '/css',
    // ADMIN_CSS_BUILD: src_path + '/dist/admin/css/*.css',

    ADMIN_JS_VENDOR_SRC: [
        node_modules_path + '/jquery/dist/jquery.js',
        node_modules_path + '/bootstrap/dist/js/bootstrap.js',
        node_modules_path + '/datatables/media/js/jquery.dataTables.min.js',
        node_modules_path + '/datatables/media/js/dataTables.bootstrap.min.js',
        node_modules_path + '/lodash-compat/index.js',
        node_modules_path + '/moment/min/moment.min.js',
        node_modules_path + '/leaflet/dist/leaflet.js',
        node_modules_path + '/highcharts-release/highcharts.js',
        node_modules_path + '/backbone/backbone.js'
    ],
    ADMIN_JS_APP_SRC: admin_src_path + '/js/**/*.js',
    ADMIN_JS_ENTRY_POINT_PREFIX: admin_src_path + '/js/',
    // note: these are file names only, not full paths...
    // they get concat'ed with ADMIN_JS_SRC_DIR in the bundling process
    ADMIN_JS_ENTRY_POINTS: [
        'account-overview.js',
        'view-data.js',
        'view-survey.js',
        'user-admin.js'
    ],
    ADMIN_JS_DIST: admin_dist_path + '/js',

    ADMIN_IMG_SRC: admin_src_path + '/img/**/*',
    ADMIN_IMG_DIST: admin_dist_path + '/img',

    ADMIN_FONT_SRC: [
        node_modules_path + '/bootstrap/fonts/*'
    ],
    ADMIN_FONT_DIST: admin_dist_path + '/fonts',

    ADMIN_TEMPLATES_SRC: admin_src_path + '/templates/**/*'
};


var admin_tasks = ['admin-less', 'admin-js-vendor', 'admin-js-app', 'admin-img', 'admin-fonts'],
    survey_tasks = ['survey-less', 'survey-js-vendor', 'survey-js-app', 'survey-img', 'survey-fonts', 'survey-app-cache'];


process.env.BROWSERIFYSHIM_DIAGNOSTICS=1;

//---------------------
// SURVEY TASKS

/**
 * Copies the cache manifest file, incrementing the version #
 */
gulp.task('survey-app-cache', function() {
    gulp.src(path.APP_CACHE_SRC)
        .pipe(replace(/\$date/g, Date.now()))
        .pipe(gulp.dest(path.APP_CACHE_DIST));
});

// Concat all vendor dependencies
gulp.task('survey-js-vendor', function() {
    gulp.src( path.SURVEY_JS_VENDOR_SRC )
       .pipe(concat('vendor.js'))
       .pipe(gulp.dest(path.SURVEY_JS_DIST));
});

gulp.task('survey-js-app', function() {
    return browserify({ entries: [path.SURVEY_JS_ENTRY_POINT] })
        .transform(reactify)
        .bundle()
        .on('error', function (err) {
            console.log(err.message);
            process.exit(1);
            this.emit('end');
        })
        .pipe(source(path.JS_BUILD_FILENAME))
        // rename them to have "bundle as postfix"
        .pipe(rename({
            extname: '.bundle.js'
        }))
        .pipe(gulp.dest(path.SURVEY_JS_DIST));
});

// Custom LESS compiling
gulp.task('survey-less', function() {
    // survey
    gulp.src(path.SURVEY_LESS_ENTRY_POINT)
        .pipe(less())
        // handle errors so the compiler doesn't stop
        .on('error', function (err) {
            console.log(err.message);
            this.emit('end');
        })
        .pipe(gulp.dest(path.SURVEY_CSS_DIST));
});

// Copy survey images to dist directory
gulp.task('survey-img', function() {
    gulp.src([path.SURVEY_IMG_SRC, path.COMMON_IMG_SRC])
        .pipe(gulp.dest(path.SURVEY_IMG_DIST));
});

// Move fonts to dist directory
gulp.task('survey-fonts', function() {
    gulp.src(path.SURVEY_FONT_SRC)
        .pipe(gulp.dest(path.SURVEY_FONT_DIST));
});

gulp.task('survey-watch',
    ['survey-less', 'survey-js-vendor', 'survey-js-app', 'survey-img', 'survey-fonts', 'survey-app-cache'],
    function() {
        livereload.listen();
        gulp.watch([path.SURVEY_LESS_SRC, path.SURVEY_JS_APP_SRC, path.APP_CACHE_SRC],
            ['survey-less', 'survey-js-vendor', 'survey-js-app', 'survey-img', 'survey-fonts', 'survey-app-cache']);
    });



//---------------------
// ADMIN TASKS

// Concat all vendor dependencies
gulp.task('admin-js-vendor', function() {
    gulp.src( path.ADMIN_JS_VENDOR_SRC )
       .pipe(concat('vendor.js'))
       .pipe(gulp.dest(path.ADMIN_JS_DIST));
});

gulp.task('admin-js-app', function() {
    var tasks = path.ADMIN_JS_ENTRY_POINTS.map(function(entry) {
        // note appending of root path to entry here
        return browserify({ entries: [path.ADMIN_JS_ENTRY_POINT_PREFIX + entry] })
            .transform(underscorify)
            .bundle()
            .on('error', function (err) {
                console.log(err.message);
                this.emit('end');
                process.exit(1);
            })
            .pipe(source(entry))
            // rename them to have "bundle as postfix"
            .pipe(rename({
                extname: '.bundle.js'
            }))
            .pipe(gulp.dest(path.ADMIN_JS_DIST));
    });
    return es.merge.apply(null, tasks);
});

gulp.task('admin-less', function() {
    // admin
    gulp.src(path.ADMIN_LESS_ENTRY_POINT)
        .pipe(less())
        // handle errors so the compiler doesn't stop
        .on('error', function (err) {
            console.log(err.message);
            this.emit('end');
        })
        .pipe(gulp.dest(path.ADMIN_CSS_DIST));
});

// Copy admin images to dist directory
gulp.task('admin-img', function() {
    gulp.src([path.ADMIN_IMG_SRC, path.COMMON_IMG_SRC])
        .pipe(gulp.dest(path.ADMIN_IMG_DIST));
});

// Move fonts to dist directory
gulp.task('admin-fonts', function() {
    gulp.src(path.ADMIN_FONT_SRC)
        .pipe(gulp.dest(path.ADMIN_FONT_DIST));
});

gulp.task('admin-watch',
    ['admin-less', 'admin-js-vendor', 'admin-js-app', 'admin-img', 'admin-fonts'],
    function() {
        livereload.listen();
        gulp.watch([path.ADMIN_LESS_SRC, path.ADMIN_JS_APP_SRC, path.ADMIN_TEMPLATES_SRC],
            ['admin-less', 'admin-js-vendor', 'admin-js-app', 'admin-img', 'admin-fonts']);
    });


//
// DEV TASKS
//
gulp.task('dev-build', admin_tasks.concat(survey_tasks));


//
// PROD TASKS
//
gulp.task('build', function() {
    browserify({
        entries: [path.JS_ENTRY_POINT],
        transform: [reactify]
    })
    .bundle()
    .pipe(source(path.JS_MINIFIED_BUILD_FILENAME))
    .pipe(streamify(uglify(path.JS_MINIFIED_BUILD_FILENAME)))
    .pipe(gulp.dest(path.JS_DEST_BUILD));
});



// DEFAULT TASK

gulp.task('watch', ['survey-watch', 'admin-watch']);

gulp.task('default', ['watch']);
