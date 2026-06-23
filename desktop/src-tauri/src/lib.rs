mod backend;
mod connection;

use std::sync::Mutex;

use serde::Serialize;
use tauri::{AppHandle, Manager, RunEvent, State};
use tauri_plugin_dialog::DialogExt;

use backend::{start_backend, stop_backend, BackendState};
use connection::{
    is_api_healthy_at, read_connection_config, write_connection_config, ConnectionConfig, LOCAL_API,
};

#[derive(Default)]
struct BackendBoot {
    error: Mutex<Option<String>>,
}

#[derive(Serialize)]
struct AppInfo {
    name: &'static str,
    version: &'static str,
    platform: &'static str,
    api_url: String,
    cloud_api_url: Option<String>,
}

#[derive(Serialize)]
struct BackendStatus {
    ready: bool,
    error: Option<String>,
    cloud_configured: bool,
    cloud_online: bool,
}

fn optional_string(value: String) -> Option<String> {
    if value.trim().is_empty() {
        None
    } else {
        Some(value)
    }
}

#[tauri::command]
fn get_app_info(app: AppHandle) -> Result<AppInfo, String> {
    let data_dir = app.path().app_data_dir().map_err(|e| e.to_string())?;
    let config = read_connection_config(&data_dir);
    Ok(AppInfo {
        name: "MDA ERP",
        version: env!("CARGO_PKG_VERSION"),
        platform: "desktop",
        api_url: LOCAL_API.to_string(),
        cloud_api_url: optional_string(config.cloud_api_base),
    })
}

#[tauri::command]
fn get_backend_status(app: AppHandle, boot: State<'_, BackendBoot>) -> Result<BackendStatus, String> {
    let data_dir = app.path().app_data_dir().map_err(|e| e.to_string())?;
    let config = read_connection_config(&data_dir);
    let error = boot.error.lock().ok().and_then(|g| g.clone());
    let local_ok = error.is_none() && is_api_healthy_at(LOCAL_API);
    let cloud_online = optional_string(config.cloud_api_base.clone())
        .map(|url| is_api_healthy_at(&url))
        .unwrap_or(false);
    Ok(BackendStatus {
        ready: local_ok,
        error,
        cloud_configured: config.has_cloud(),
        cloud_online,
    })
}

#[tauri::command]
fn get_connection_config(app: AppHandle) -> Result<ConnectionConfig, String> {
    let data_dir = app.path().app_data_dir().map_err(|e| e.to_string())?;
    Ok(read_connection_config(&data_dir))
}

#[tauri::command]
fn save_connection_config(app: AppHandle, config: ConnectionConfig) -> Result<(), String> {
    let data_dir = app.path().app_data_dir().map_err(|e| e.to_string())?;
    write_connection_config(&data_dir, &config)
}

#[tauri::command]
fn save_pdf_file(app: tauri::AppHandle, filename: String, data: Vec<u8>) -> Result<Option<String>, String> {
    let path = app
        .dialog()
        .file()
        .set_file_name(&filename)
        .add_filter("PDF Document", &["pdf"])
        .blocking_save_file();

    match path {
        Some(file_path) => {
            let dest = file_path.into_path().map_err(|e| e.to_string())?;
            std::fs::write(&dest, &data).map_err(|e| e.to_string())?;
            Ok(Some(dest.to_string_lossy().into_owned()))
        }
        None => Ok(None),
    }
}

fn spawn_backend_async(app: AppHandle) {
    std::thread::spawn(move || {
        match start_backend(&app) {
            Ok(state) => {
                app.manage(state);
                log::info!("MDA local API started (offline-first)");
            }
            Err(err) => {
                log::error!("MDA API failed to start: {err}");
                if let Some(boot) = app.try_state::<BackendBoot>() {
                    if let Ok(mut guard) = boot.error.lock() {
                        *guard = Some(err);
                    }
                }
            }
        }
    });
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_shell::init())
        .manage(BackendBoot::default())
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            spawn_backend_async(app.handle().clone());
            let data_dir = app
                .path()
                .app_data_dir()
                .map_err(|e| format!("App data path error: {e}"))?;
            let config = read_connection_config(&data_dir);
            if config.has_cloud() {
                log::info!(
                    "Hybrid mode — local database + cloud sync at {}",
                    config.cloud_api_base
                );
            }

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_app_info,
            get_backend_status,
            get_connection_config,
            save_connection_config,
            save_pdf_file
        ])
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app_handle, event| {
            if let RunEvent::Exit = event {
                if let Some(state) = app_handle.try_state::<BackendState>() {
                    stop_backend(&state);
                }
            }
        });
}
