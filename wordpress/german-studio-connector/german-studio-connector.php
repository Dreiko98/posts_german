<?php
/**
 * Plugin Name: German Studio Connector
 * Description: Authenticated draft correlation and a narrowly scoped Yoast SEO writer.
 * Version: 1.0.0
 * License: GPL-2.0-or-later
 */
if (!defined('ABSPATH')) { exit; }

register_activation_hook(__FILE__, function () {
    global $wpdb;
    require_once ABSPATH . 'wp-admin/includes/upgrade.php';
    dbDelta('CREATE TABLE ' . $wpdb->prefix . 'gstudio_requests (
        request_key varchar(36) NOT NULL,
        post_id bigint(20) unsigned DEFAULT NULL,
        PRIMARY KEY (request_key)
    ) ' . $wpdb->get_charset_collate() . ';');
});

function gstudio_permission() { return current_user_can('edit_posts'); }
function gstudio_post_permission($request) { return current_user_can('edit_post', (int) $request['id']); }

function gstudio_find($key) {
    global $wpdb;
    $table = $wpdb->prefix . 'gstudio_requests';
    $id = $wpdb->get_var($wpdb->prepare("SELECT post_id FROM $table WHERE request_key=%s", $key));
    if (!$id) {
        $id = $wpdb->get_var($wpdb->prepare("SELECT post_id FROM {$wpdb->postmeta} WHERE meta_key='_gstudio_request_key' AND meta_value=%s LIMIT 1", $key));
        if ($id) { $wpdb->replace($table, array('request_key' => $key, 'post_id' => $id)); }
    }
    return $id ? (int) $id : null;
}

function gstudio_key($value) { return is_string($value) && preg_match('/^[a-f0-9-]{36}$/', $value); }

add_action('rest_api_init', function () {
    register_rest_route('german-studio/v1', '/health', array(
        'methods' => 'GET', 'permission_callback' => 'gstudio_permission',
        'callback' => function () { return array('version' => '1.0.0', 'yoast_version' => defined('WPSEO_VERSION') ? WPSEO_VERSION : null); }
    ));
    register_rest_route('german-studio/v1', '/drafts', array(
        array('methods' => 'GET', 'permission_callback' => 'gstudio_permission', 'callback' => function ($r) {
            if (!gstudio_key($r['key'])) { return new WP_Error('bad_key', 'Clave inválida', array('status' => 400)); }
            $id = gstudio_find($r['key']);
            if ($id && !current_user_can('edit_post', $id)) { return new WP_Error('forbidden', 'Sin permiso', array('status' => 403)); }
            return array('post_id' => $id);
        }),
        array('methods' => 'POST', 'permission_callback' => 'gstudio_permission', 'callback' => function ($r) {
            global $wpdb;
            $key = $r['key'];
            if (!gstudio_key($key)) { return new WP_Error('bad_key', 'Clave inválida', array('status' => 400)); }
            $lock = 'gstudio_' . hash('sha256', $key);
            $lock = substr($lock, 0, 64);
            if ((int) $wpdb->get_var($wpdb->prepare('SELECT GET_LOCK(%s, 10)', $lock)) !== 1) {
                return new WP_Error('busy', 'Creación en curso', array('status' => 409));
            }
            try {
                $correlated = gstudio_find($key);
                $id = $r['post_id'] ? (int) $r['post_id'] : $correlated;
                if ($correlated && $id !== $correlated) { return new WP_Error('key_conflict', 'La clave corresponde a otro artículo', array('status' => 409)); }
                if ($id) {
                    $post = get_post($id);
                    if (!$post || !current_user_can('edit_post', $id) || $post->post_type !== 'post') {
                        return new WP_Error('forbidden', 'Artículo no editable', array('status' => 403));
                    }
                    if (!in_array($post->post_status, array('draft', 'pending'), true)) {
                        return new WP_Error('not_draft', 'El artículo ya no es un borrador', array('status' => 409));
                    }
                    if ($r['expected_hash'] && $post->post_modified_gmt !== $r['expected_hash']) {
                        return new WP_Error('external_change', 'El artículo ha cambiado', array('status' => 409));
                    }
                    // If a create response was lost, return its existing ID without rewriting content.
                    if (!$r['post_id'] && $correlated) { return array('post_id' => $id, 'reconciled' => true); }
                }
                $title = sanitize_text_field((string) $r['title']);
                $content = wp_kses_post((string) $r['content']);
                if (!$title || strlen($content) > 500000) { return new WP_Error('bad_content', 'Contenido inválido', array('status' => 400)); }
                $fields = array('post_title' => $title, 'post_content' => $content, 'post_excerpt' => wp_kses_post((string) $r['excerpt']),
                    'post_name' => sanitize_title((string) $r['slug']), 'post_type' => 'post', 'post_status' => 'draft',
                    'post_category' => array_map('intval', (array) $r['categories']), 'tags_input' => array_map('intval', (array) $r['tags']));
                if ($id) { $fields['ID'] = $id; }
                else {
                    $fields['post_author'] = get_current_user_id();
                    $fields['meta_input'] = array('_gstudio_request_key' => $key);
                    $wpdb->query('START TRANSACTION');
                }
                $result = wp_insert_post(wp_slash($fields), true);
                if (is_wp_error($result)) { if (!$id) { $wpdb->query('ROLLBACK'); } return $result; }
                $wpdb->replace($wpdb->prefix . 'gstudio_requests', array('request_key' => $key, 'post_id' => $result));
                if (!$id) { $wpdb->query('COMMIT'); }
                return array('post_id' => $result, 'reconciled' => false);
            } finally {
                $wpdb->get_var($wpdb->prepare('SELECT RELEASE_LOCK(%s)', $lock));
            }
        })
    ));
    register_rest_route('german-studio/v1', '/posts/(?P<id>\d+)/seo', array(
        'methods' => array('GET', 'POST'), 'permission_callback' => 'gstudio_post_permission',
        'callback' => function ($r) {
            $id = (int) $r['id'];
            if (!defined('WPSEO_VERSION')) { return new WP_Error('yoast_missing', 'Yoast SEO gratuito no está instalado', array('status' => 409)); }
            $fields = array('keyphrase' => 'focuskw', 'seo_title' => 'title', 'meta_description' => 'metadesc');
            if ($r->get_method() === 'POST') {
                $body = $r->get_json_params();
                if (!is_array($body) || array_diff(array_keys($body), array_keys($fields))) {
                    return new WP_Error('bad_fields', 'Solo frase clave, título SEO y metadescripción', array('status' => 400));
                }
                foreach ($fields as $public => $yoast) {
                    if (!isset($body[$public]) || !is_string($body[$public]) || mb_strlen($body[$public]) > ($public === 'keyphrase' ? 100 : 500)) {
                        return new WP_Error('bad_value', 'Valor SEO inválido', array('status' => 400));
                    }
                }
                foreach ($fields as $public => $yoast) {
                    WPSEO_Meta::set_value($yoast, sanitize_text_field($body[$public]), $id);
                }
                // Rebuild the indexable after meta writes: the Yoast REST output reads indexables.
                if (function_exists('YoastSEO') && class_exists('Yoast\\WP\\SEO\\Builders\\Indexable_Builder')) {
                    try {
                        YoastSEO()->classes->get('Yoast\\WP\\SEO\\Builders\\Indexable_Builder')->build_for_id_and_type($id, 'post');
                    } catch (Throwable $error) {
                        return new WP_Error('yoast_indexable', 'Los metadatos se guardaron, pero la reindexación requiere revisión en Yoast', array('status' => 409));
                    }
                }
                clean_post_cache($id);
            }
            $result = array();
            foreach ($fields as $public => $yoast) { $result[$public] = WPSEO_Meta::get_value($yoast, $id); }
            return $result;
        }
    ));
});
