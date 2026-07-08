use std::path::Path;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::{Duration, Instant};

use tauri::{AppHandle, Manager};
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;

pub const LOCAL_API_PORT: u16 = 18765;

fn health_url() -> String {
    format!("http://127.0.0.1:{LOCAL_API_PORT}/api/v1/health/")
}

const STARTUP_TIMEOUT: Duration = Duration::from_secs(180);

pub fn is_api_healthy() -> bool {
    ureq::get(&health_url())
        .call()
        .map(|r| r.status() == 200)
        .unwrap_or(false)
}

enum ApiChild {
    Process(Child),
    Sidecar(CommandChild),
}

impl ApiChild {
    fn kill(self) {
        match self {
            ApiChild::Process(mut child) => {
                let _ = child.kill();
                let _ = child.wait();
            }
            ApiChild::Sidecar(child) => {
                let _ = child.kill();
            }
        }
    }

    fn has_exited(&mut self) -> bool {
        match self {
            ApiChild::Process(child) => child.try_wait().ok().flatten().is_some(),
            ApiChild::Sidecar(_) => false,
        }
    }
}

pub struct BackendState {
    child: Mutex<Option<ApiChild>>,
}

impl BackendState {
    pub fn shutdown(&self) {
        if let Ok(mut guard) = self.child.lock() {
            if let Some(child) = guard.take() {
                child.kill();
            }
        }
    }
}

impl Drop for BackendState {
    fn drop(&mut self) {
        self.shutdown();
    }
}

fn backend_source_dir() -> std::path::PathBuf {
    std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../backend")
}

fn resolve_python() -> String {
    if cfg!(windows) {
        if Command::new("py")
            .arg("-3")
            .arg("--version")
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status()
            .map(|s| s.success())
            .unwrap_or(false)
        {
            return "py".into();
        }
    }
    "python".into()
}

fn python_args(python: &str) -> Vec<String> {
    if python == "py" {
        vec!["-3".into()]
    } else {
        vec![]
    }
}

fn kill_stale_sidecar() {
    #[cfg(windows)]
    {
        let _ = Command::new("taskkill")
            .args(["/F", "/IM", "mda-api.exe", "/T"])
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status();
    }
}

fn read_api_error_log(data_dir: &Path) -> Option<String> {
    let log_path = data_dir.join("mda-api-error.log");
    let text = std::fs::read_to_string(log_path).ok()?;
    let trimmed = text.trim();
    if trimmed.is_empty() {
        None
    } else {
        Some(trimmed.chars().take(800).collect())
    }
}

fn spawn_dev_backend(data_dir: &Path) -> Result<ApiChild, String> {
    let backend_dir = backend_source_dir();
    let server_script = backend_dir.join("desktop_server.py");
    if !server_script.is_file() {
        return Err(format!(
            "Backend not found at {}. Run from the MDA repository.",
            backend_dir.display()
        ));
    }

    let python = resolve_python();
    let mut args = python_args(&python);
    args.push(server_script.to_string_lossy().into_owned());

    let mut cmd = Command::new(&python);
    cmd.args(&args)
        .current_dir(&backend_dir)
        .env("DJANGO_SETTINGS_MODULE", "config.settings.desktop")
        .env("MDA_DATA_DIR", data_dir)
        .env("MDA_API_PORT", LOCAL_API_PORT.to_string())
        .stdout(Stdio::null())
        .stderr(Stdio::null());

    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x08000000;
        cmd.creation_flags(CREATE_NO_WINDOW);
    }

    let child = cmd.spawn().map_err(|e| {
        format!(
            "Dev mode: install Python 3.11+ and pip install -r backend/requirements/desktop.txt\n{e}"
        )
    })?;

    Ok(ApiChild::Process(child))
}

fn spawn_sidecar(app: &AppHandle, data_dir: &Path) -> Result<ApiChild, String> {
    kill_stale_sidecar();

    let sidecar = app
        .shell()
        .sidecar("mda-api")
        .map_err(|e| {
            format!(
                "Bundled API missing from installer. Rebuild with make build-desktop.\n{e}"
            )
        })?;

    let (_rx, child) = sidecar
        .env("MDA_DATA_DIR", data_dir.to_string_lossy().to_string())
        .env("DJANGO_SETTINGS_MODULE", "config.settings.desktop")
        .env("MDA_API_PORT", LOCAL_API_PORT.to_string())
        .spawn()
        .map_err(|e| format!("Failed to start bundled MDA API: {e}"))?;

    Ok(ApiChild::Sidecar(child))
}

fn wait_for_api(child: &mut ApiChild, data_dir: &Path) -> Result<(), String> {
    let url = health_url();
    let deadline = Instant::now() + STARTUP_TIMEOUT;
    while Instant::now() < deadline {
        if child.has_exited() {
            let detail = read_api_error_log(data_dir).unwrap_or_else(|| {
                "The bundled API process exited during startup.".into()
            });
            return Err(format!(
                "Local API stopped unexpectedly.\n{detail}\n\nLog: {}",
                data_dir.join("mda-api-error.log").display()
            ));
        }
        if let Ok(response) = ureq::get(&url).call() {
            if response.status() == 200 {
                return Ok(());
            }
        }
        std::thread::sleep(Duration::from_millis(400));
    }

    let detail = read_api_error_log(data_dir).unwrap_or_default();
    let mut message = format!(
        "Local API did not start in time (port {LOCAL_API_PORT}). Close other MDA ERP windows and retry."
    );
    if !detail.is_empty() {
        message.push_str(&format!("\n\n{detail}"));
    }
    message.push_str(&format!(
        "\n\nDetails: {}",
        data_dir.join("mda-api-error.log").display()
    ));
    Err(message)
}

pub fn start_backend(app: &AppHandle) -> Result<BackendState, String> {
    let data_dir = app
        .path()
        .app_data_dir()
        .map_err(|e| format!("App data path error: {e}"))?;
    std::fs::create_dir_all(&data_dir).map_err(|e| format!("Could not create app data dir: {e}"))?;

    log::info!("MDA data directory: {}", data_dir.display());

    let mut child = if cfg!(debug_assertions) {
        spawn_dev_backend(&data_dir)?
    } else {
        spawn_sidecar(app, &data_dir)?
    };

    wait_for_api(&mut child, &data_dir)?;

    Ok(BackendState {
        child: Mutex::new(Some(child)),
    })
}

pub fn stop_backend(state: &BackendState) {
    state.shutdown();
}
