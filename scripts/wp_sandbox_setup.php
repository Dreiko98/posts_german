<?php
define('WP_INSTALLING', true);
$_SERVER['HTTP_HOST'] = '127.0.0.1:18081';
$_SERVER['REQUEST_URI'] = '/';
$_SERVER['SERVER_PROTOCOL'] = 'HTTP/1.1';
// CLI installation must have a valid site URL even when rerunning after an interrupted setup.
$db = new mysqli(getenv('WORDPRESS_DB_HOST'), getenv('WORDPRESS_DB_USER'), getenv('WORDPRESS_DB_PASSWORD'), getenv('WORDPRESS_DB_NAME'));
if ($db->query("SHOW TABLES LIKE 'wp_options'")->num_rows) {
    $db->query("UPDATE wp_options SET option_value='http://127.0.0.1:18081' WHERE option_name IN ('home','siteurl')");
}
$db->close();
require '/var/www/html/wp-load.php';
require_once ABSPATH . 'wp-admin/includes/upgrade.php';
require_once ABSPATH . 'wp-admin/includes/plugin.php';
if (!is_blog_installed()) {
    wp_install('Entorno de pruebas German Studio', 'test-admin', 'test@example.invalid', 0, '', 'test-only-password-strong');
}
$user = get_user_by('login', 'test-admin');
update_option('siteurl', 'http://127.0.0.1:18081');
update_option('home', 'http://127.0.0.1:18081');
wp_set_current_user($user->ID);
activate_plugin('wordpress-seo/wp-seo.php');
activate_plugin('german-studio-connector/german-studio-connector.php');
update_option('permalink_structure', '/%postname%/');
flush_rewrite_rules();
$password = WP_Application_Passwords::create_new_application_password($user->ID, array('name' => 'tests'));
file_put_contents('/tmp/test-app-password', $password[0]);
echo 'WordPress instalado con plugins de pruebas.';
