use std::path::{Path, PathBuf};



use serde::{Deserialize, Serialize};



pub const LOCAL_API: &str = "http://127.0.0.1:8000/api/v1";



#[derive(Serialize, Deserialize, Default, Clone)]

pub struct ConnectionConfig {

    #[serde(default, rename = "cloud_api_base")]

    pub cloud_api_base: String,

    #[serde(default, rename = "tenant_slug")]

    pub tenant_slug: String,

    #[serde(default, rename = "sync_secret")]

    pub sync_secret: String,

    /// Legacy api_base field from older builds.

    #[serde(default, rename = "api_base")]

    pub api_base: String,

}



impl ConnectionConfig {

    pub fn normalized(mut self) -> Self {

        if self.cloud_api_base.trim().is_empty() && !self.api_base.trim().is_empty() {

            let legacy = self.api_base.trim();

            if !is_local_api_base(legacy) {

                self.cloud_api_base = legacy.trim_end_matches('/').to_string();

            }

        }

        self.cloud_api_base = self.cloud_api_base.trim().trim_end_matches('/').to_string();

        self.tenant_slug = self.tenant_slug.trim().to_string();

        self.sync_secret = self.sync_secret.trim().to_string();

        self

    }



    pub fn has_cloud(&self) -> bool {

        !self.cloud_api_base.is_empty()

    }

}



pub fn connection_config_path(data_dir: &Path) -> PathBuf {

    data_dir.join("connection.json")

}



pub fn read_connection_config(data_dir: &Path) -> ConnectionConfig {

    let path = connection_config_path(data_dir);

    let text = std::fs::read_to_string(path).unwrap_or_default();

    if text.trim().is_empty() {

        return ConnectionConfig::default();

    }

    serde_json::from_str(&text)

        .map(|c: ConnectionConfig| c.normalized())

        .unwrap_or_default()

}



pub fn write_connection_config(data_dir: &Path, config: &ConnectionConfig) -> Result<(), String> {

    std::fs::create_dir_all(data_dir).map_err(|e| e.to_string())?;

    let normalized = config.clone().normalized();

    let path = connection_config_path(data_dir);

    if !normalized.has_cloud()

        && normalized.tenant_slug.is_empty()

        && normalized.sync_secret.is_empty()

    {

        let _ = std::fs::remove_file(&path);

        return Ok(());

    }

    std::fs::write(

        path,

        serde_json::to_string_pretty(&normalized).map_err(|e| e.to_string())?,

    )

    .map_err(|e| e.to_string())

}



pub fn read_cloud_api_base(data_dir: &Path) -> Option<String> {

    let config = read_connection_config(data_dir);

    if config.cloud_api_base.is_empty() {

        None

    } else {

        Some(config.cloud_api_base)

    }

}



pub fn is_local_api_base(api_base: &str) -> bool {

    let lower = api_base.to_lowercase();

    lower.contains("127.0.0.1") || lower.contains("localhost")

}



pub fn resolved_api_base(_data_dir: &Path) -> String {

    LOCAL_API.to_string()

}



pub fn health_url(api_base: &str) -> String {

    format!("{}/health/", api_base.trim_end_matches('/'))

}



pub fn is_api_healthy_at(api_base: &str) -> bool {

    let url = health_url(api_base);

    ureq::get(&url).call().map(|r| r.status() == 200).unwrap_or(false)

}


