"""
Internationalization (i18n) system for TOWT Planning App.

Languages: fr (default), en, es, pt-br, vi
Usage in templates: {{ t('key') }} or {{ t('key', lang='en') }}
Usage in Python: from app.i18n import get_t; t = get_t('en'); t('key')
"""

SUPPORTED_LANGUAGES = {
    "fr": "Français",
    "en": "English",
    "es": "Español",
    "pt-br": "Português (BR)",
    "vi": "Tiếng Việt",
}

DEFAULT_LANG = "fr"

# ─── TRANSLATIONS ───────────────────────────────────────────────
# Keys are grouped by module. Missing keys fall back to French.
# ────────────────────────────────────────────────────────────────

TRANSLATIONS = {
    # ═══ COMMON / GLOBAL ═══
    "save": {"fr": "Enregistrer", "en": "Save", "es": "Guardar", "pt-br": "Salvar", "vi": "Lưu"},
    "cancel": {"fr": "Annuler", "en": "Cancel", "es": "Cancelar", "pt-br": "Cancelar", "vi": "Hủy"},
    "delete": {"fr": "Supprimer", "en": "Delete", "es": "Eliminar", "pt-br": "Excluir", "vi": "Xóa"},
    "edit": {"fr": "Modifier", "en": "Edit", "es": "Editar", "pt-br": "Editar", "vi": "Sửa"},
    "back": {"fr": "Retour", "en": "Back", "es": "Volver", "pt-br": "Voltar", "vi": "Quay lại"},
    "add": {"fr": "Ajouter", "en": "Add", "es": "Añadir", "pt-br": "Adicionar", "vi": "Thêm"},
    "close": {"fr": "Fermer", "en": "Close", "es": "Cerrar", "pt-br": "Fechar", "vi": "Đóng"},
    "search": {"fr": "Rechercher", "en": "Search", "es": "Buscar", "pt-br": "Buscar", "vi": "Tìm kiếm"},
    "yes": {"fr": "Oui", "en": "Yes", "es": "Sí", "pt-br": "Sim", "vi": "Có"},
    "no": {"fr": "Non", "en": "No", "es": "No", "pt-br": "Não", "vi": "Không"},
    "actions": {"fr": "Actions", "en": "Actions", "es": "Acciones", "pt-br": "Ações", "vi": "Hành động"},
    "status": {"fr": "Statut", "en": "Status", "es": "Estado", "pt-br": "Status", "vi": "Trạng thái"},
    "date": {"fr": "Date", "en": "Date", "es": "Fecha", "pt-br": "Data", "vi": "Ngày"},
    "loading": {"fr": "Chargement...", "en": "Loading...", "es": "Cargando...", "pt-br": "Carregando...", "vi": "Đang tải..."},
    "confirm_delete": {"fr": "Confirmer la suppression ?", "en": "Confirm deletion?", "es": "¿Confirmar eliminación?", "pt-br": "Confirmar exclusão?", "vi": "Xác nhận xóa?"},
    "none": {"fr": "Aucun", "en": "None", "es": "Ninguno", "pt-br": "Nenhum", "vi": "Không có"},
    "all": {"fr": "Tous", "en": "All", "es": "Todos", "pt-br": "Todos", "vi": "Tất cả"},
    "not_specified": {"fr": "Non renseigné", "en": "Not specified", "es": "No indicado", "pt-br": "Não informado", "vi": "Chưa điền"},

    # ═══ SIDEBAR / NAV ═══
    "nav_dashboard": {"fr": "Tableau de bord", "en": "Dashboard", "es": "Panel", "pt-br": "Painel", "vi": "Bảng điều khiển"},
    "nav_planning": {"fr": "Planning", "en": "Planning", "es": "Planificación", "pt-br": "Planejamento", "vi": "Kế hoạch"},
    "nav_commercial": {"fr": "Commercial", "en": "Commercial", "es": "Comercial", "pt-br": "Comercial", "vi": "Thương mại"},
    "nav_escale": {"fr": "Escale", "en": "Port Call", "es": "Escala", "pt-br": "Escala", "vi": "Ghé cảng"},
    "nav_cargo": {"fr": "Cargo Docs", "en": "Cargo Docs", "es": "Docs Carga", "pt-br": "Docs Carga", "vi": "Hồ sơ hàng"},
    "nav_kpi": {"fr": "KPI", "en": "KPI", "es": "KPI", "pt-br": "KPI", "vi": "KPI"},
    "nav_finance": {"fr": "Finance", "en": "Finance", "es": "Finanzas", "pt-br": "Finanças", "vi": "Tài chính"},
    "nav_captain": {"fr": "Capitaine", "en": "Captain", "es": "Capitán", "pt-br": "Capitão", "vi": "Thuyền trưởng"},
    "nav_crew": {"fr": "Équipage", "en": "Crew", "es": "Tripulación", "pt-br": "Tripulação", "vi": "Thủy thủ đoàn"},
    "nav_settings": {"fr": "Paramètres", "en": "Settings", "es": "Configuración", "pt-br": "Configurações", "vi": "Cài đặt"},

    # ═══ PACKING LIST (client-facing) ═══
    "pl_title": {"fr": "Packing List", "en": "Packing List", "es": "Lista de empaque", "pt-br": "Lista de embalagem", "vi": "Danh sách đóng gói"},
    "pl_locked_msg": {"fr": "Cette packing list a été verrouillée par l'exploitation. Les modifications ne sont plus possibles.",
                      "en": "This packing list has been locked by operations. Modifications are no longer possible.",
                      "es": "Esta lista de empaque ha sido bloqueada por operaciones. Ya no es posible modificarla.",
                      "pt-br": "Esta lista de embalagem foi bloqueada pela operação. Modificações não são mais possíveis.",
                      "vi": "Danh sách đóng gói này đã bị khóa bởi bộ phận vận hành. Không thể sửa đổi."},
    "pl_saved_msg": {"fr": "Vos informations ont été enregistrées avec succès.",
                     "en": "Your information has been saved successfully.",
                     "es": "Su información ha sido guardada con éxito.",
                     "pt-br": "Suas informações foram salvas com sucesso.",
                     "vi": "Thông tin của bạn đã được lưu thành công."},
    "pl_voyage_info": {"fr": "Informations voyage (pré-remplies par TOWT)", "en": "Voyage information (pre-filled by TOWT)",
                       "es": "Información del viaje (prellenada por TOWT)", "pt-br": "Informações da viagem (preenchidas pela TOWT)",
                       "vi": "Thông tin chuyến đi (được TOWT điền sẵn)"},
    "pl_shipper_section": {"fr": "Expéditeur & destinataire", "en": "Shipper & consignee",
                           "es": "Expedidor y destinatario", "pt-br": "Embarcador e destinatário",
                           "vi": "Người gửi & người nhận"},
    "pl_goods_section": {"fr": "Marchandise", "en": "Goods", "es": "Mercancía", "pt-br": "Mercadoria", "vi": "Hàng hóa"},
    "pl_dimensions_section": {"fr": "Dimensions par palette", "en": "Dimensions per pallet",
                              "es": "Dimensiones por paleta", "pt-br": "Dimensões por palete",
                              "vi": "Kích thước mỗi pallet"},
    "pl_add_batch": {"fr": "Ajouter un batch", "en": "Add a batch", "es": "Añadir un lote",
                     "pt-br": "Adicionar um lote", "vi": "Thêm lô hàng"},
    "pl_delete_batch": {"fr": "Supprimer ce batch", "en": "Delete this batch", "es": "Eliminar este lote",
                        "pt-br": "Excluir este lote", "vi": "Xóa lô hàng này"},
    "pl_batch": {"fr": "Batch", "en": "Batch", "es": "Lote", "pt-br": "Lote", "vi": "Lô hàng"},

    # Fields
    "f_voyage": {"fr": "Voyage", "en": "Voyage", "es": "Viaje", "pt-br": "Viagem", "vi": "Chuyến đi"},
    "f_vessel": {"fr": "Navire", "en": "Vessel", "es": "Buque", "pt-br": "Navio", "vi": "Tàu"},
    "f_loading_date": {"fr": "Date de chargement", "en": "Loading date", "es": "Fecha de carga", "pt-br": "Data de embarque", "vi": "Ngày xếp hàng"},
    "f_freight_rate": {"fr": "Fret/palette", "en": "Freight/pallet", "es": "Flete/paleta", "pt-br": "Frete/palete", "vi": "Cước/pallet"},
    "f_customer_name": {"fr": "Nom client", "en": "Customer name", "es": "Nombre del cliente", "pt-br": "Nome do cliente", "vi": "Tên khách hàng"},
    "f_freight_forwarder": {"fr": "Transitaire", "en": "Freight forwarder", "es": "Transitario", "pt-br": "Agente de carga", "vi": "Đại lý giao nhận"},
    "f_code_transitaire": {"fr": "Code transitaire", "en": "Forwarder code", "es": "Código transitario", "pt-br": "Código agente", "vi": "Mã đại lý"},
    "f_shipper_name": {"fr": "Nom expéditeur (Shipper)", "en": "Shipper name", "es": "Nombre del expedidor", "pt-br": "Nome do embarcador", "vi": "Tên người gửi"},
    "f_shipper_address": {"fr": "Adresse expéditeur", "en": "Shipper address", "es": "Dirección del expedidor", "pt-br": "Endereço do embarcador", "vi": "Địa chỉ người gửi"},
    "f_po_number": {"fr": "N° PO", "en": "PO number", "es": "N° PO", "pt-br": "N° PO", "vi": "Số PO"},
    "f_batch_id": {"fr": "Batch ID client", "en": "Client batch ID", "es": "ID lote cliente", "pt-br": "ID lote cliente", "vi": "Mã lô khách hàng"},
    "f_notify_address": {"fr": "Adresse Notify", "en": "Notify address", "es": "Dirección Notify", "pt-br": "Endereço Notify", "vi": "Địa chỉ Notify"},
    "f_consignee_address": {"fr": "Adresse Consignee", "en": "Consignee address", "es": "Dirección Consignee", "pt-br": "Endereço Consignatário", "vi": "Địa chỉ người nhận"},
    "f_pallet_type": {"fr": "Type de palette", "en": "Pallet type", "es": "Tipo de paleta", "pt-br": "Tipo de palete", "vi": "Loại pallet"},
    "f_type_of_goods": {"fr": "Nature des marchandises", "en": "Type of goods", "es": "Tipo de mercancía", "pt-br": "Tipo de mercadoria", "vi": "Loại hàng hóa"},
    "f_bio_products": {"fr": "Produits bio", "en": "Organic products", "es": "Productos bio", "pt-br": "Produtos orgânicos", "vi": "Sản phẩm hữu cơ"},
    "f_pallet_quantity": {"fr": "Nb palettes ce batch", "en": "Pallets in this batch", "es": "Paletas en este lote", "pt-br": "Paletes neste lote", "vi": "Số pallet trong lô"},
    "f_cases_quantity": {"fr": "Nb colis", "en": "Cases qty", "es": "Cant. bultos", "pt-br": "Qtd. volumes", "vi": "Số kiện"},
    "f_units_per_case": {"fr": "Unités/colis", "en": "Units/case", "es": "Unidades/bulto", "pt-br": "Unidades/volume", "vi": "Đơn vị/kiện"},
    "f_imo_class": {"fr": "Classification IMO", "en": "IMO classification", "es": "Clasificación OMI", "pt-br": "Classificação IMO", "vi": "Phân loại IMO"},
    "f_cargo_value": {"fr": "Valeur cargo (USD)", "en": "Cargo value (USD)", "es": "Valor carga (USD)", "pt-br": "Valor carga (USD)", "vi": "Giá trị hàng (USD)"},
    "f_length": {"fr": "Longueur (cm)", "en": "Length (cm)", "es": "Largo (cm)", "pt-br": "Comprimento (cm)", "vi": "Dài (cm)"},
    "f_width": {"fr": "Largeur (cm)", "en": "Width (cm)", "es": "Ancho (cm)", "pt-br": "Largura (cm)", "vi": "Rộng (cm)"},
    "f_height": {"fr": "Hauteur (cm)", "en": "Height (cm)", "es": "Alto (cm)", "pt-br": "Altura (cm)", "vi": "Cao (cm)"},
    "f_weight": {"fr": "Poids brut (kg)", "en": "Gross weight (kg)", "es": "Peso bruto (kg)", "pt-br": "Peso bruto (kg)", "vi": "Trọng lượng (kg)"},
    "help_length": {"fr": "Longueur extérieure palette, emballage compris", "en": "Outer pallet length incl. packaging",
                    "es": "Largo exterior del palet, embalaje incluido", "pt-br": "Comprimento externo do palete, incluindo embalagem",
                    "vi": "Chiều dài ngoài pallet, bao gồm bao bì"},
    "help_width": {"fr": "Largeur extérieure palette, emballage compris", "en": "Outer pallet width incl. packaging",
                   "es": "Ancho exterior del palet, embalaje incluido", "pt-br": "Largura externa do palete, incluindo embalagem",
                   "vi": "Chiều rộng ngoài pallet, bao gồm bao bì"},
    "help_height": {"fr": "Hauteur totale du sol au sommet des marchandises, palette incluse", "en": "Total height from floor to top of goods, pallet included",
                    "es": "Altura total del suelo a la parte superior de la mercancía, palet incluido", "pt-br": "Altura total do chão ao topo das mercadorias, palete incluído",
                    "vi": "Tổng chiều cao từ sàn đến đỉnh hàng hóa, bao gồm pallet"},
    "help_weight": {"fr": "Poids brut par palette : marchandises + palette + emballage", "en": "Gross weight per pallet: goods + pallet + wrapping",
                    "es": "Peso bruto por palet: mercancía + palet + embalaje", "pt-br": "Peso bruto por palete: mercadorias + palete + embalagem",
                    "vi": "Trọng lượng gộp mỗi pallet: hàng + pallet + bao bì"},
    "f_ordered_palettes": {"fr": "Palettes commandées", "en": "Ordered pallets", "es": "Paletas pedidas", "pt-br": "Paletes pedidos", "vi": "Pallet đã đặt"},
    "f_loading": {"fr": "Chargement", "en": "Loading", "es": "Carga", "pt-br": "Embarque", "vi": "Xếp hàng"},
    "f_destination": {"fr": "Destination", "en": "Destination", "es": "Destino", "pt-br": "Destino", "vi": "Điểm đến"},
    "f_other": {"fr": "Autre", "en": "Other", "es": "Otro", "pt-br": "Outro", "vi": "Khác"},

    # ═══ EXPLOITATION CARGO ═══
    "cargo_title": {"fr": "Gestion documentaire cargo", "en": "Cargo document management",
                    "es": "Gestión documental de carga", "pt-br": "Gestão documental de carga",
                    "vi": "Quản lý hồ sơ hàng hóa"},
    "cargo_draft": {"fr": "Brouillon", "en": "Draft", "es": "Borrador", "pt-br": "Rascunho", "vi": "Nháp"},
    "cargo_submitted": {"fr": "Soumis", "en": "Submitted", "es": "Enviado", "pt-br": "Enviado", "vi": "Đã gửi"},
    "cargo_locked": {"fr": "Verrouillé", "en": "Locked", "es": "Bloqueado", "pt-br": "Bloqueado", "vi": "Đã khóa"},
    "cargo_reviewed": {"fr": "Examiné", "en": "Reviewed", "es": "Revisado", "pt-br": "Revisado", "vi": "Đã xem"},
    "cargo_lock": {"fr": "Verrouiller", "en": "Lock", "es": "Bloquear", "pt-br": "Bloquear", "vi": "Khóa"},
    "cargo_unlock": {"fr": "Déverrouiller", "en": "Unlock", "es": "Desbloquear", "pt-br": "Desbloquear", "vi": "Mở khóa"},
    "cargo_history": {"fr": "Historique", "en": "History", "es": "Historial", "pt-br": "Histórico", "vi": "Lịch sử"},
    "cargo_import_excel": {"fr": "Import Excel", "en": "Import Excel", "es": "Importar Excel", "pt-br": "Importar Excel", "vi": "Nhập Excel"},
    "cargo_export_excel": {"fr": "Export Excel", "en": "Export Excel", "es": "Exportar Excel", "pt-br": "Exportar Excel", "vi": "Xuất Excel"},
    "cargo_bill_of_lading": {"fr": "Bill of Lading", "en": "Bill of Lading", "es": "Conocimiento de embarque", "pt-br": "Conhecimento de embarque", "vi": "Vận đơn"},
    "cargo_completion": {"fr": "Complétude", "en": "Completion", "es": "Completitud", "pt-br": "Conclusão", "vi": "Hoàn thành"},
    "cargo_client_link": {"fr": "Lien client", "en": "Client link", "es": "Enlace cliente", "pt-br": "Link cliente", "vi": "Liên kết khách hàng"},
    "cargo_palette_ok": {"fr": "palettes — Conforme", "en": "pallets — Compliant", "es": "paletas — Conforme", "pt-br": "paletes — Conforme", "vi": "pallet — Phù hợp"},
    "cargo_palette_over": {"fr": "Excédent de", "en": "Excess of", "es": "Excedente de", "pt-br": "Excesso de", "vi": "Dư"},
    "cargo_palette_under": {"fr": "Manque", "en": "Missing", "es": "Faltan", "pt-br": "Faltam", "vi": "Thiếu"},
    "cargo_palette_gap": {"fr": "Écart palettes", "en": "Pallet discrepancy", "es": "Discrepancia paletas", "pt-br": "Discrepância paletes", "vi": "Chênh lệch pallet"},
    "cargo_in_batches": {"fr": "dans les batchs", "en": "in batches", "es": "en lotes", "pt-br": "nos lotes", "vi": "trong các lô"},
    "cargo_ordered": {"fr": "commandée(s)", "en": "ordered", "es": "pedida(s)", "pt-br": "pedido(s)", "vi": "đã đặt"},

    # ═══ SETTINGS ═══
    "settings_title": {"fr": "Paramètres", "en": "Settings", "es": "Configuración", "pt-br": "Configurações", "vi": "Cài đặt"},
    "settings_language": {"fr": "Langue de l'interface", "en": "Interface language", "es": "Idioma de la interfaz", "pt-br": "Idioma da interface", "vi": "Ngôn ngữ giao diện"},
    "settings_saved": {"fr": "Paramètres enregistrés", "en": "Settings saved", "es": "Configuración guardada", "pt-br": "Configurações salvas", "vi": "Đã lưu cài đặt"},

    # ═══ BACKOFFICE — PAGE TITLES ═══
    "page_dashboard": {"fr": "Tableau de bord", "en": "Dashboard", "es": "Panel", "pt-br": "Painel", "vi": "Bảng điều khiển"},
    "page_planning": {"fr": "Planification", "en": "Planning", "es": "Planificación", "pt-br": "Planejamento", "vi": "Kế hoạch"},
    "page_commercial": {"fr": "Ordres de transport", "en": "Freight orders", "es": "Órdenes de transporte", "pt-br": "Ordens de transporte", "vi": "Đơn vận chuyển"},
    "page_escale": {"fr": "Opérations d'escale", "en": "Port call operations", "es": "Operaciones de escala", "pt-br": "Operações de escala", "vi": "Hoạt động cảng"},
    "page_cargo": {"fr": "Gestion documentaire cargo", "en": "Cargo document management", "es": "Gestión documental carga", "pt-br": "Gestão documental carga", "vi": "Quản lý hồ sơ hàng"},
    "page_onboard": {"fr": "On Board", "en": "On Board", "es": "A bordo", "pt-br": "A bordo", "vi": "Trên tàu"},
    "page_crew": {"fr": "Gestion d'équipage", "en": "Crew management", "es": "Gestión de tripulación", "pt-br": "Gestão de tripulação", "vi": "Quản lý thủy thủ đoàn"},
    "page_finance": {"fr": "Suivi financier", "en": "Financial tracking", "es": "Seguimiento financiero", "pt-br": "Acompanhamento financeiro", "vi": "Theo dõi tài chính"},
    "page_port_config": {"fr": "Configuration des ports", "en": "Port configuration", "es": "Configuración de puertos", "pt-br": "Configuração de portos", "vi": "Cấu hình cảng"},
    "page_kpi": {"fr": "KPI", "en": "KPI", "es": "KPI", "pt-br": "KPI", "vi": "KPI"},
    "page_claims": {"fr": "Claims", "en": "Claims", "es": "Siniestros", "pt-br": "Sinistros", "vi": "Khiếu nại"},
    "page_new_claim": {"fr": "Nouveau Claim", "en": "New Claim", "es": "Nuevo siniestro", "pt-br": "Novo sinistro", "vi": "Khiếu nại mới"},
    "page_captain": {"fr": "Vue Capitaine", "en": "Captain view", "es": "Vista Capitán", "pt-br": "Visão do Capitão", "vi": "Giao diện Thuyền trưởng"},
    "page_settings": {"fr": "Paramètres", "en": "Settings", "es": "Configuración", "pt-br": "Configurações", "vi": "Cài đặt"},
    "page_my_account": {"fr": "Mon compte", "en": "My account", "es": "Mi cuenta", "pt-br": "Minha conta", "vi": "Tài khoản"},
    "page_history": {"fr": "Historique", "en": "History", "es": "Historial", "pt-br": "Histórico", "vi": "Lịch sử"},
    "page_port_conflicts": {"fr": "Vue par port — Surveillance des escales", "en": "Port view — Call monitoring", "es": "Vista por puerto — Vigilancia", "pt-br": "Vista por porto — Monitoramento", "vi": "Theo cảng — Giám sát"},

    # ═══ BACKOFFICE — DASHBOARD ═══
    "dash_welcome": {"fr": "Bienvenue,", "en": "Welcome,", "es": "Bienvenido,", "pt-br": "Bem-vindo,", "vi": "Xin chào,"},
    "dash_subtitle": {"fr": "TOWT — Transport à la voile · Gestion de la flotte", "en": "TOWT — Sailing transport · Fleet management", "es": "TOWT — Transporte a vela · Gestión de flota", "pt-br": "TOWT — Transporte à vela · Gestão de frota", "vi": "TOWT — Vận tải buồm · Quản lý đội tàu"},
    "dash_notifications": {"fr": "Notifications", "en": "Notifications", "es": "Notificaciones", "pt-br": "Notificações", "vi": "Thông báo"},
    "dash_archive_read": {"fr": "Archiver les lus", "en": "Archive read", "es": "Archivar leídos", "pt-br": "Arquivar lidos", "vi": "Lưu trữ đã đọc"},
    "dash_mark_read": {"fr": "Marquer lu", "en": "Mark as read", "es": "Marcar leído", "pt-br": "Marcar lido", "vi": "Đánh dấu đã đọc"},
    "dash_mark_unread": {"fr": "Marquer non lu", "en": "Mark as unread", "es": "Marcar no leído", "pt-br": "Marcar não lido", "vi": "Đánh dấu chưa đọc"},
    "dash_archive": {"fr": "Archiver", "en": "Archive", "es": "Archivar", "pt-br": "Arquivar", "vi": "Lưu trữ"},
    "dash_packing_to_review": {"fr": "Packing Lists à traiter", "en": "Packing Lists to review", "es": "Listas de empaque a revisar", "pt-br": "Listas de embalagem a revisar", "vi": "Danh sách cần xem"},
    "dash_alerts": {"fr": "Alertes", "en": "Alerts", "es": "Alertas", "pt-br": "Alertas", "vi": "Cảnh báo"},
    "dash_hide_show": {"fr": "Masquer/Afficher", "en": "Hide/Show", "es": "Ocultar/Mostrar", "pt-br": "Ocultar/Mostrar", "vi": "Ẩn/Hiện"},
    "dash_fleet": {"fr": "Flotte TOWT", "en": "TOWT Fleet", "es": "Flota TOWT", "pt-br": "Frota TOWT", "vi": "Đội tàu TOWT"},
    "dash_tracking_map": {"fr": "Suivi GPS de la flotte", "en": "Fleet GPS Tracking", "es": "Seguimiento GPS de la flota", "pt-br": "Rastreamento GPS da frota", "vi": "Theo dõi GPS đội tàu"},
    "dash_upcoming": {"fr": "Prochains départs", "en": "Upcoming departures", "es": "Próximas salidas", "pt-br": "Próximas partidas", "vi": "Khởi hành sắp tới"},
    "dash_quick_access": {"fr": "Accès rapide", "en": "Quick access", "es": "Acceso rápido", "pt-br": "Acesso rápido", "vi": "Truy cập nhanh"},
    "dash_legs": {"fr": "Legs", "en": "Legs", "es": "Tramos", "pt-br": "Trechos", "vi": "Chặng"},
    "dash_active_orders": {"fr": "Commandes actives", "en": "Active orders", "es": "Pedidos activos", "pt-br": "Pedidos ativos", "vi": "Đơn hàng"},
    "dash_calls_month": {"fr": "Escales ce mois", "en": "Port calls this month", "es": "Escalas este mes", "pt-br": "Escalas este mês", "vi": "Ghé cảng tháng này"},
    "dash_revenue_forecast": {"fr": "CA prév.", "en": "Revenue fcst.", "es": "Ing. prev.", "pt-br": "Rec. prev.", "vi": "DT dự kiến"},
    "dash_co2_avoided": {"fr": "CO₂ évité", "en": "CO₂ avoided", "es": "CO₂ evitado", "pt-br": "CO₂ evitado", "vi": "CO₂ tránh"},
    "dash_fill_rate": {"fr": "Remplissage moy.", "en": "Avg fill rate", "es": "Llenado prom.", "pt-br": "Taxa méd.", "vi": "Tỷ lệ TB"},
    "dash_treated": {"fr": "Traité", "en": "Treated", "es": "Tratado", "pt-br": "Tratado", "vi": "Đã xử lý"},
    "dash_view": {"fr": "Voir", "en": "View", "es": "Ver", "pt-br": "Ver", "vi": "Xem"},

    # ═══ BACKOFFICE — SIDEBAR ═══
    "nav_onboard": {"fr": "On Board", "en": "On Board", "es": "A bordo", "pt-br": "A bordo", "vi": "Trên tàu"},
    "nav_claims": {"fr": "Claims", "en": "Claims", "es": "Siniestros", "pt-br": "Sinistros", "vi": "Khiếu nại"},
    "nav_my_account": {"fr": "Mon compte", "en": "My account", "es": "Mi cuenta", "pt-br": "Minha conta", "vi": "Tài khoản"},
    "nav_logout": {"fr": "Déconnexion", "en": "Logout", "es": "Cerrar sesión", "pt-br": "Sair", "vi": "Đăng xuất"},
    "nav_administration": {"fr": "Administration", "en": "Administration", "es": "Administración", "pt-br": "Administração", "vi": "Quản trị"},
    "nav_navigation": {"fr": "Navigation", "en": "Navigation", "es": "Navegación", "pt-br": "Navegação", "vi": "Điều hướng"},

    # ═══ BACKOFFICE — COMMON TABLE HEADERS ═══
    "th_reference": {"fr": "Référence", "en": "Reference", "es": "Referencia", "pt-br": "Referência", "vi": "Mã"},
    "th_client": {"fr": "Client", "en": "Client", "es": "Cliente", "pt-br": "Cliente", "vi": "Khách hàng"},
    "th_vessel": {"fr": "Navire", "en": "Vessel", "es": "Buque", "pt-br": "Navio", "vi": "Tàu"},
    "th_leg": {"fr": "Leg", "en": "Leg", "es": "Tramo", "pt-br": "Trecho", "vi": "Chặng"},
    "th_route": {"fr": "Route", "en": "Route", "es": "Ruta", "pt-br": "Rota", "vi": "Tuyến"},
    "th_departure": {"fr": "Départ", "en": "Departure", "es": "Salida", "pt-br": "Partida", "vi": "Khởi hành"},
    "th_arrival": {"fr": "Arrivée", "en": "Arrival", "es": "Llegada", "pt-br": "Chegada", "vi": "Đến"},
    "th_palettes": {"fr": "Palettes", "en": "Pallets", "es": "Paletas", "pt-br": "Paletes", "vi": "Pallet"},
    "th_amount": {"fr": "Montant", "en": "Amount", "es": "Importe", "pt-br": "Valor", "vi": "Số tiền"},
    "th_year": {"fr": "Année", "en": "Year", "es": "Año", "pt-br": "Ano", "vi": "Năm"},
    "th_type": {"fr": "Type", "en": "Type", "es": "Tipo", "pt-br": "Tipo", "vi": "Loại"},
    "th_cabin": {"fr": "Cabine", "en": "Cabin", "es": "Camarote", "pt-br": "Cabine", "vi": "Phòng"},
    "th_total": {"fr": "Total", "en": "Total", "es": "Total", "pt-br": "Total", "vi": "Tổng"},
    "th_provision": {"fr": "Provision", "en": "Provision", "es": "Provisión", "pt-br": "Provisão", "vi": "Dự phòng"},
    "th_distance": {"fr": "Distance NM", "en": "Distance NM", "es": "Distancia MN", "pt-br": "Distância MN", "vi": "Khoảng cách HL"},
    "th_duration": {"fr": "Durée jours", "en": "Duration days", "es": "Duración días", "pt-br": "Duração dias", "vi": "Thời gian ngày"},

    # ═══ BACKOFFICE — COMMON BUTTONS ═══
    "btn_new_order": {"fr": "Nouvelle commande", "en": "New order", "es": "Nuevo pedido", "pt-br": "Novo pedido", "vi": "Đơn mới"},
    "btn_new_claim": {"fr": "Nouveau Claim", "en": "New Claim", "es": "Nuevo siniestro", "pt-br": "Novo sinistro", "vi": "Khiếu nại mới"},
    "btn_new_leg": {"fr": "Nouveau leg", "en": "New leg", "es": "Nuevo tramo", "pt-br": "Novo trecho", "vi": "Chặng mới"},
    "btn_export": {"fr": "Exporter", "en": "Export", "es": "Exportar", "pt-br": "Exportar", "vi": "Xuất"},
    "btn_import": {"fr": "Importer", "en": "Import", "es": "Importar", "pt-br": "Importar", "vi": "Nhập"},
    "btn_filter": {"fr": "Filtrer", "en": "Filter", "es": "Filtrar", "pt-br": "Filtrar", "vi": "Lọc"},
    "btn_print": {"fr": "Imprimer", "en": "Print", "es": "Imprimir", "pt-br": "Imprimir", "vi": "In"},
    "btn_update": {"fr": "Mettre à jour", "en": "Update", "es": "Actualizar", "pt-br": "Atualizar", "vi": "Cập nhật"},
    "btn_send": {"fr": "Envoyer", "en": "Send", "es": "Enviar", "pt-br": "Enviar", "vi": "Gửi"},
    "btn_reply": {"fr": "Répondre", "en": "Reply", "es": "Responder", "pt-br": "Responder", "vi": "Trả lời"},
    "btn_mark_read": {"fr": "Marquer comme lus", "en": "Mark as read", "es": "Marcar como leídos", "pt-br": "Marcar como lidos", "vi": "Đánh dấu đã đọc"},
    "btn_create": {"fr": "Créer", "en": "Create", "es": "Crear", "pt-br": "Criar", "vi": "Tạo"},

    # ═══ BACKOFFICE — STATUSES ═══
    "status_draft": {"fr": "Brouillon", "en": "Draft", "es": "Borrador", "pt-br": "Rascunho", "vi": "Nháp"},
    "status_confirmed": {"fr": "Confirmé", "en": "Confirmed", "es": "Confirmado", "pt-br": "Confirmado", "vi": "Đã xác nhận"},
    "status_cancelled": {"fr": "Annulé", "en": "Cancelled", "es": "Cancelado", "pt-br": "Cancelado", "vi": "Đã hủy"},
    "status_completed": {"fr": "Terminé", "en": "Completed", "es": "Completado", "pt-br": "Concluído", "vi": "Hoàn thành"},
    "status_at_port": {"fr": "À quai", "en": "At port", "es": "En muelle", "pt-br": "No cais", "vi": "Tại cảng"},
    "status_at_sea": {"fr": "En mer", "en": "At sea", "es": "En el mar", "pt-br": "No mar", "vi": "Trên biển"},
    "status_reserved": {"fr": "Réservé", "en": "Reserved", "es": "Reservado", "pt-br": "Reservado", "vi": "Đã đặt"},
    "status_unassigned": {"fr": "Non affecté", "en": "Unassigned", "es": "Sin asignar", "pt-br": "Não atribuído", "vi": "Chưa phân"},

    # ═══ BACKOFFICE — MY ACCOUNT ═══
    "account_info": {"fr": "Informations", "en": "Information", "es": "Información", "pt-br": "Informações", "vi": "Thông tin"},
    "account_full_name": {"fr": "Nom complet", "en": "Full name", "es": "Nombre completo", "pt-br": "Nome completo", "vi": "Họ tên"},
    "account_username": {"fr": "Identifiant", "en": "Username", "es": "Identificador", "pt-br": "Usuário", "vi": "Tên đăng nhập"},
    "account_role": {"fr": "Rôle", "en": "Role", "es": "Rol", "pt-br": "Função", "vi": "Vai trò"},
    "account_language": {"fr": "Langue d'affichage", "en": "Display language", "es": "Idioma de visualización", "pt-br": "Idioma de exibição", "vi": "Ngôn ngữ hiển thị"},
    "account_change_password": {"fr": "Changer le mot de passe", "en": "Change password", "es": "Cambiar contraseña", "pt-br": "Alterar senha", "vi": "Đổi mật khẩu"},
    "account_current_password": {"fr": "Mot de passe actuel", "en": "Current password", "es": "Contraseña actual", "pt-br": "Senha atual", "vi": "Mật khẩu hiện tại"},
    "account_new_password": {"fr": "Nouveau mot de passe", "en": "New password", "es": "Nueva contraseña", "pt-br": "Nova senha", "vi": "Mật khẩu mới"},
    "account_confirm_password": {"fr": "Confirmer", "en": "Confirm", "es": "Confirmar", "pt-br": "Confirmar", "vi": "Xác nhận"},

    # ═══ BACKOFFICE — NOTIFICATIONS ═══
    "notif_new_order": {"fr": "Nouvelle commande client", "en": "New client order", "es": "Nuevo pedido", "pt-br": "Novo pedido", "vi": "Đơn hàng mới"},
    "notif_new_cargo_message": {"fr": "Nouveau message messagerie client", "en": "New client message", "es": "Nuevo mensaje cliente", "pt-br": "Nova mensagem cliente", "vi": "Tin nhắn mới"},
    "notif_eosp": {"fr": "EOSP (End of Sea Passage)", "en": "EOSP (End of Sea Passage)", "es": "EOSP", "pt-br": "EOSP", "vi": "EOSP"},
    "notif_sosp": {"fr": "SOSP (Start of Sea Passage)", "en": "SOSP (Start of Sea Passage)", "es": "SOSP", "pt-br": "SOSP", "vi": "SOSP"},

    # ═══ BACKOFFICE — CLAIMS ═══
    "claim_financial": {"fr": "Suivi financier", "en": "Financial tracking", "es": "Seguimiento financiero", "pt-br": "Acompanhamento financeiro", "vi": "Theo dõi tài chính"},
    "claim_provision": {"fr": "Provision", "en": "Provision", "es": "Provisión", "pt-br": "Provisão", "vi": "Dự phòng"},
    "claim_franchise": {"fr": "Franchise", "en": "Deductible", "es": "Franquicia", "pt-br": "Franquia", "vi": "Khấu trừ"},
    "claim_indemnity": {"fr": "Prise en charge assureur", "en": "Insurer coverage", "es": "Cobertura aseguradora", "pt-br": "Cobertura seguradora", "vi": "Bảo hiểm chi trả"},
    "claim_company_charge": {"fr": "Reste à charge", "en": "Company charge", "es": "A cargo empresa", "pt-br": "Custo empresa", "vi": "Phí công ty"},
    "claim_responsibility": {"fr": "Responsabilité", "en": "Responsibility", "es": "Responsabilidad", "pt-br": "Responsabilidade", "vi": "Trách nhiệm"},
    "claim_voyage": {"fr": "Voyage", "en": "Voyage", "es": "Viaje", "pt-br": "Viagem", "vi": "Chuyến đi"},

    # ═══ BACKOFFICE — MESSAGES ═══
    "msg_reply_cargo_placeholder": {"fr": "Répondre au client…", "en": "Reply to client…", "es": "Responder al cliente…", "pt-br": "Responder ao cliente…", "vi": "Trả lời khách hàng…"},
    "msg_no_messages": {"fr": "Aucun message", "en": "No messages", "es": "Sin mensajes", "pt-br": "Sem mensagens", "vi": "Không có tin nhắn"},
    "msg_unread": {"fr": "non lu(s)", "en": "unread", "es": "no leído(s)", "pt-br": "não lido(s)", "vi": "chưa đọc"},
    "msg_messages": {"fr": "Messages", "en": "Messages", "es": "Mensajes", "pt-br": "Mensagens", "vi": "Tin nhắn"},

    # ═══ BACKOFFICE — COMMERCIAL ═══
    "com_new": {"fr": "Nouveau", "en": "New", "es": "Nuevo", "pt-br": "Novo", "vi": "Mới"},
    "com_all": {"fr": "Tous", "en": "All", "es": "Todos", "pt-br": "Todos", "vi": "Tất cả"},
    "com_ref": {"fr": "Réf.", "en": "Ref.", "es": "Ref.", "pt-br": "Ref.", "vi": "Mã"},
    "com_client": {"fr": "Client", "en": "Client", "es": "Cliente", "pt-br": "Cliente", "vi": "Khách hàng"},
    "com_palettes": {"fr": "Palettes", "en": "Pallets", "es": "Paletas", "pt-br": "Paletes", "vi": "Pallet"},
    "com_format": {"fr": "Format", "en": "Format", "es": "Formato", "pt-br": "Formato", "vi": "Loại"},
    "com_fees": {"fr": "Frais", "en": "Fees", "es": "Costes", "pt-br": "Taxas", "vi": "Phí"},
    "com_total": {"fr": "Total", "en": "Total", "es": "Total", "pt-br": "Total", "vi": "Tổng"},
    "com_desired_route": {"fr": "Route souhaitée", "en": "Desired route", "es": "Ruta deseada", "pt-br": "Rota desejada", "vi": "Tuyến yêu cầu"},
    "com_assignment": {"fr": "Affectation", "en": "Assignment", "es": "Asignación", "pt-br": "Atribuição", "vi": "Phân bổ"},
    "com_status": {"fr": "Statut", "en": "Status", "es": "Estado", "pt-br": "Status", "vi": "Trạng thái"},
    "com_attachment": {"fr": "PJ", "en": "Att.", "es": "Adj.", "pt-br": "Anexo", "vi": "Đính kèm"},
    "com_actions": {"fr": "Actions", "en": "Actions", "es": "Acciones", "pt-br": "Ações", "vi": "Hành động"},
    "com_no_orders": {"fr": "Aucun ordre de transport", "en": "No freight orders", "es": "Sin órdenes de transporte", "pt-br": "Nenhuma ordem de transporte", "vi": "Không có đơn vận chuyển"},
    "com_edit": {"fr": "Modifier", "en": "Edit", "es": "Editar", "pt-br": "Editar", "vi": "Sửa"},
    "com_assign": {"fr": "Affecter", "en": "Assign", "es": "Asignar", "pt-br": "Atribuir", "vi": "Phân bổ"},
    "com_attachment_label": {"fr": "Pièce jointe", "en": "Attachment", "es": "Archivo adjunto", "pt-br": "Anexo", "vi": "Đính kèm"},
    "com_file_label": {"fr": "Fichier (PDF ou Word)", "en": "File (PDF or Word)", "es": "Archivo (PDF o Word)", "pt-br": "Arquivo (PDF ou Word)", "vi": "Tệp (PDF hoặc Word)"},
    "com_delete_confirm": {"fr": "Supprimer", "en": "Delete", "es": "Eliminar", "pt-br": "Excluir", "vi": "Xóa"},
    "com_new_order": {"fr": "Nouvel ordre de transport", "en": "New freight order", "es": "Nueva orden de transporte", "pt-br": "Nova ordem de transporte", "vi": "Đơn vận chuyển mới"},
    "com_edit_order": {"fr": "Modifier", "en": "Edit", "es": "Modificar", "pt-br": "Modificar", "vi": "Sửa"},
    "com_assign_order": {"fr": "Affecter", "en": "Assign", "es": "Asignar", "pt-br": "Atribuir", "vi": "Phân bổ"},
    "com_desired_delivery": {"fr": "Livraison souhaitée", "en": "Desired delivery", "es": "Entrega deseada", "pt-br": "Entrega desejada", "vi": "Giao hàng mong muốn"},
    "com_suggestion": {"fr": "Suggestion", "en": "Suggestion", "es": "Sugerencia", "pt-br": "Sugestão", "vi": "Gợi ý"},

    # ═══ BACKOFFICE — ESCALE ═══
    "esc_no_ops": {"fr": "Aucune opération d'escale", "en": "No port call operations", "es": "Sin operaciones de escala", "pt-br": "Sem operações de escala", "vi": "Không có hoạt động cảng"},
    "esc_port": {"fr": "Port", "en": "Port", "es": "Puerto", "pt-br": "Porto", "vi": "Cảng"},
    "esc_vessel": {"fr": "Navire", "en": "Vessel", "es": "Buque", "pt-br": "Navio", "vi": "Tàu"},
    "esc_eta": {"fr": "ETA", "en": "ETA", "es": "ETA", "pt-br": "ETA", "vi": "ETA"},
    "esc_etd": {"fr": "ETD", "en": "ETD", "es": "ETD", "pt-br": "ETD", "vi": "ETD"},
    "esc_sof": {"fr": "SOF", "en": "SOF", "es": "SOF", "pt-br": "SOF", "vi": "SOF"},
    "esc_operations": {"fr": "Opérations", "en": "Operations", "es": "Operaciones", "pt-br": "Operações", "vi": "Hoạt động"},

    # ═══ BACKOFFICE — CREW ═══
    "crew_member": {"fr": "Membre", "en": "Member", "es": "Miembro", "pt-br": "Membro", "vi": "Thành viên"},
    "crew_role": {"fr": "Fonction", "en": "Role", "es": "Función", "pt-br": "Função", "vi": "Chức vụ"},
    "crew_phone": {"fr": "Téléphone", "en": "Phone", "es": "Teléfono", "pt-br": "Telefone", "vi": "Điện thoại"},
    "crew_email": {"fr": "Email", "en": "Email", "es": "Email", "pt-br": "Email", "vi": "Email"},
    "crew_nationality": {"fr": "Nationalité", "en": "Nationality", "es": "Nacionalidad", "pt-br": "Nacionalidade", "vi": "Quốc tịch"},
    "crew_certifications": {"fr": "Brevets", "en": "Certifications", "es": "Certificados", "pt-br": "Certificados", "vi": "Chứng chỉ"},
    "crew_calendar": {"fr": "Calendrier", "en": "Calendar", "es": "Calendario", "pt-br": "Calendário", "vi": "Lịch"},
    "crew_new_member": {"fr": "Nouveau membre", "en": "New member", "es": "Nuevo miembro", "pt-br": "Novo membro", "vi": "Thêm thành viên"},
    "crew_assignments": {"fr": "Affectations", "en": "Assignments", "es": "Asignaciones", "pt-br": "Atribuições", "vi": "Phân công"},
    "crew_no_members": {"fr": "Aucun membre d'équipage", "en": "No crew members", "es": "Sin tripulantes", "pt-br": "Sem membros", "vi": "Không có thành viên"},

    # ═══ BACKOFFICE — FINANCE ═══
    "fin_revenue": {"fr": "Recettes", "en": "Revenue", "es": "Ingresos", "pt-br": "Receitas", "vi": "Doanh thu"},
    "fin_expenses": {"fr": "Dépenses", "en": "Expenses", "es": "Gastos", "pt-br": "Despesas", "vi": "Chi phí"},
    "fin_balance": {"fr": "Solde", "en": "Balance", "es": "Saldo", "pt-br": "Saldo", "vi": "Số dư"},
    "fin_invoices": {"fr": "Factures", "en": "Invoices", "es": "Facturas", "pt-br": "Faturas", "vi": "Hóa đơn"},
    "fin_payments": {"fr": "Paiements", "en": "Payments", "es": "Pagos", "pt-br": "Pagamentos", "vi": "Thanh toán"},
    "fin_year": {"fr": "Année", "en": "Year", "es": "Año", "pt-br": "Ano", "vi": "Năm"},
    "fin_vessel": {"fr": "Navire", "en": "Vessel", "es": "Buque", "pt-br": "Navio", "vi": "Tàu"},
    "fin_all_vessels": {"fr": "Tous les navires", "en": "All vessels", "es": "Todos los buques", "pt-br": "Todos os navios", "vi": "Tất cả tàu"},
    "fin_no_data": {"fr": "Aucune donnée financière", "en": "No financial data", "es": "Sin datos financieros", "pt-br": "Sem dados financeiros", "vi": "Không có dữ liệu"},

    # ═══ BACKOFFICE — PASSENGERS ═══

    # ═══ BACKOFFICE — PLANNING ═══
    "plan_gantt": {"fr": "Gantt", "en": "Gantt", "es": "Gantt", "pt-br": "Gantt", "vi": "Gantt"},
    "plan_list": {"fr": "Liste", "en": "List", "es": "Lista", "pt-br": "Lista", "vi": "Danh sách"},
    "plan_new_leg": {"fr": "Nouveau leg", "en": "New leg", "es": "Nuevo tramo", "pt-br": "Novo trecho", "vi": "Chặng mới"},
    "plan_vessel": {"fr": "Navire", "en": "Vessel", "es": "Buque", "pt-br": "Navio", "vi": "Tàu"},
    "plan_leg_code": {"fr": "Code leg", "en": "Leg code", "es": "Código", "pt-br": "Código", "vi": "Mã chặng"},
    "plan_route": {"fr": "Route", "en": "Route", "es": "Ruta", "pt-br": "Rota", "vi": "Tuyến"},
    "plan_departure": {"fr": "Départ", "en": "Departure", "es": "Salida", "pt-br": "Partida", "vi": "Khởi hành"},
    "plan_arrival": {"fr": "Arrivée", "en": "Arrival", "es": "Llegada", "pt-br": "Chegada", "vi": "Đến"},
    "plan_status": {"fr": "Statut", "en": "Status", "es": "Estado", "pt-br": "Status", "vi": "Trạng thái"},
    "plan_distance": {"fr": "Distance NM", "en": "Distance NM", "es": "Distancia MN", "pt-br": "Distância MN", "vi": "Khoảng cách HL"},
    "plan_duration": {"fr": "Durée jours", "en": "Duration days", "es": "Duración días", "pt-br": "Duração dias", "vi": "Thời gian ngày"},
    "plan_cargo": {"fr": "Cargo", "en": "Cargo", "es": "Carga", "pt-br": "Carga", "vi": "Hàng"},
    "plan_pax": {"fr": "Pax", "en": "Pax", "es": "Pax", "pt-br": "Pax", "vi": "Khách"},
    "plan_fill": {"fr": "Remplissage", "en": "Fill rate", "es": "Llenado", "pt-br": "Taxa", "vi": "Tỷ lệ"},
    "plan_no_legs": {"fr": "Aucun leg", "en": "No legs", "es": "Sin tramos", "pt-br": "Sem trechos", "vi": "Không có chặng"},
    "plan_all_vessels": {"fr": "Tous", "en": "All", "es": "Todos", "pt-br": "Todos", "vi": "Tất cả"},
    "plan_year": {"fr": "Année", "en": "Year", "es": "Año", "pt-br": "Ano", "vi": "Năm"},
    "plan_port_view": {"fr": "Vue ports", "en": "Port view", "es": "Vista puertos", "pt-br": "Vista portos", "vi": "Theo cảng"},

    # ═══ BACKOFFICE — KPI ═══
    "kpi_performance": {"fr": "Performance opérationnelle", "en": "Operational performance", "es": "Rendimiento operacional", "pt-br": "Performance operacional", "vi": "Hiệu suất"},
    "kpi_claims": {"fr": "Sinistralité", "en": "Claims rate", "es": "Siniestralidad", "pt-br": "Sinistralidade", "vi": "Tỷ lệ khiếu nại"},
    "kpi_emissions": {"fr": "Émissions CO₂", "en": "CO₂ emissions", "es": "Emisiones CO₂", "pt-br": "Emissões CO₂", "vi": "Khí thải CO₂"},
    "kpi_no_data": {"fr": "Aucune donnée KPI", "en": "No KPI data", "es": "Sin datos KPI", "pt-br": "Sem dados KPI", "vi": "Không có dữ liệu KPI"},

    # ═══ BACKOFFICE — ON BOARD ═══
    "ob_select_vessel": {"fr": "Sélectionnez un navire", "en": "Select a vessel", "es": "Seleccione un buque", "pt-br": "Selecione um navio", "vi": "Chọn tàu"},
    "ob_current_leg": {"fr": "Leg en cours", "en": "Current leg", "es": "Tramo actual", "pt-br": "Trecho atual", "vi": "Chặng hiện tại"},
    "ob_no_current": {"fr": "Aucun leg en cours", "en": "No current leg", "es": "Sin tramo actual", "pt-br": "Sem trecho atual", "vi": "Không có chặng"},
    "ob_daily_report": {"fr": "Rapport journalier", "en": "Daily report", "es": "Informe diario", "pt-br": "Relatório diário", "vi": "Báo cáo hằng ngày"},
    "ob_sof": {"fr": "Statement of Facts", "en": "Statement of Facts", "es": "Statement of Facts", "pt-br": "Statement of Facts", "vi": "Statement of Facts"},
    "ob_log": {"fr": "Journal de bord", "en": "Logbook", "es": "Bitácora", "pt-br": "Diário de bordo", "vi": "Nhật ký"},

    # ═══ BACKOFFICE — ADMIN / SETTINGS ═══
    "admin_users": {"fr": "Gestion des utilisateurs", "en": "User management", "es": "Gestión de usuarios", "pt-br": "Gestão de usuários", "vi": "Quản lý người dùng"},
    "admin_vessels": {"fr": "Navires", "en": "Vessels", "es": "Buques", "pt-br": "Navios", "vi": "Tàu"},
    "admin_ports": {"fr": "Ports", "en": "Ports", "es": "Puertos", "pt-br": "Portos", "vi": "Cảng"},
    "admin_database": {"fr": "Base de données", "en": "Database", "es": "Base de datos", "pt-br": "Banco de dados", "vi": "Cơ sở dữ liệu"},
    "admin_general": {"fr": "Général", "en": "General", "es": "General", "pt-br": "Geral", "vi": "Chung"},
    "admin_opex": {"fr": "OPEX", "en": "OPEX", "es": "OPEX", "pt-br": "OPEX", "vi": "OPEX"},
    "admin_emissions": {"fr": "Émissions", "en": "Emissions", "es": "Emisiones", "pt-br": "Emissões", "vi": "Khí thải"},
    "admin_insurance": {"fr": "Assurances", "en": "Insurance", "es": "Seguros", "pt-br": "Seguros", "vi": "Bảo hiểm"},
    "admin_export_full": {"fr": "Export complet", "en": "Full export", "es": "Exportación completa", "pt-br": "Exportação completa", "vi": "Xuất toàn bộ"},
    "admin_export_selective": {"fr": "Export sélectif", "en": "Selective export", "es": "Exportación selectiva", "pt-br": "Exportação seletiva", "vi": "Xuất chọn lọc"},
    "admin_export_files": {"fr": "Export fichiers", "en": "Export files", "es": "Exportar archivos", "pt-br": "Exportar arquivos", "vi": "Xuất tệp"},
    "admin_purge": {"fr": "Vider sélection", "en": "Purge selection", "es": "Vaciar selección", "pt-br": "Limpar seleção", "vi": "Xóa chọn"},
    "admin_reset": {"fr": "Réinitialiser", "en": "Reset", "es": "Reiniciar", "pt-br": "Reiniciar", "vi": "Đặt lại"},
    "admin_stats": {"fr": "Stats BDD", "en": "DB Stats", "es": "Estadísticas BD", "pt-br": "Estatísticas BD", "vi": "Thống kê CSDL"},
    "admin_cleanup": {"fr": "Nettoyage", "en": "Cleanup", "es": "Limpieza", "pt-br": "Limpeza", "vi": "Dọn dẹp"},
    "admin_danger_zone": {"fr": "Zone de danger", "en": "Danger zone", "es": "Zona de peligro", "pt-br": "Zona de perigo", "vi": "Vùng nguy hiểm"},
    "admin_new_user": {"fr": "Nouvel utilisateur", "en": "New user", "es": "Nuevo usuario", "pt-br": "Novo usuário", "vi": "Người dùng mới"},

    # ═══ DOCUMENT GENERATION ═══
    "doc_choose_lang": {"fr": "Choisir la langue du document", "en": "Choose document language",
                        "es": "Elegir idioma del documento", "pt-br": "Escolher idioma do documento",
                        "vi": "Chọn ngôn ngữ tài liệu"},
    "doc_generate": {"fr": "Générer", "en": "Generate", "es": "Generar", "pt-br": "Gerar", "vi": "Tạo"},
    "doc_french_english_only": {"fr": "Français ou Anglais uniquement", "en": "French or English only",
                                "es": "Solo francés o inglés", "pt-br": "Apenas francês ou inglês",
                                "vi": "Chỉ tiếng Pháp hoặc tiếng Anh"},

    # ═══ CARGO CLIENT PORTAL ═══
    "cp_packing_list": {"fr": "Packing List", "en": "Packing List", "es": "Lista de empaque", "pt-br": "Lista de embalagem", "vi": "Danh sách đóng gói"},
    "cp_vessel": {"fr": "Le Navire", "en": "The Vessel", "es": "El Buque", "pt-br": "O Navio", "vi": "Tàu"},
    "cp_voyage": {"fr": "Le Voyage", "en": "The Voyage", "es": "El Viaje", "pt-br": "A Viagem", "vi": "Chuyến đi"},
    "cp_stowage": {"fr": "Position", "en": "Position", "es": "Posicion", "pt-br": "Posicao", "vi": "Vi tri"},
    "cp_guide": {"fr": "Guide client", "en": "Client Guide"},
    "guide_toc": {"fr": "Sommaire", "en": "Table of Contents"},
    "guide_tip": {"fr": "Conseil", "en": "Tip"},
    "guide_important": {"fr": "Important", "en": "Important"},
    "guide_field": {"fr": "Champ", "en": "Field"},
    "guide_required": {"fr": "Obligatoire", "en": "Required"},
    "guide_description": {"fr": "Description", "en": "Description"},
    "guide_example": {"fr": "Exemple", "en": "Example"},
    "guide_optional": {"fr": "Optionnel", "en": "Optional"},
    "guide_recommended": {"fr": "Recommandé", "en": "Recommended"},
    "guide_situation": {"fr": "Situation", "en": "Situation"},
    "guide_fee": {"fr": "Frais", "en": "Fee"},

    # Section 1 — Overview
    "guide_s1_title": {"fr": "Présentation du portail", "en": "Portal Overview"},
    "guide_s1_p1": {
        "fr": "Ce portail vous permet de renseigner et suivre vos expéditions de marchandises à bord des voiliers-cargos TOWT. Vous y trouverez toutes les informations nécessaires pour compléter votre packing list, suivre le voyage de vos marchandises et communiquer avec notre équipe opérations.",
        "en": "This portal allows you to enter and track your cargo shipments aboard TOWT sailing cargo vessels. Here you will find all the information needed to complete your packing list, track your cargo's voyage and communicate with our operations team.",
    },
    "guide_s1_p2": {
        "fr": "Chaque onglet du menu latéral correspond à une étape du processus : packing list, informations navire, suivi du voyage, documents et messagerie.",
        "en": "Each tab in the sidebar corresponds to a step in the process: packing list, vessel information, voyage tracking, documents and messaging.",
    },
    "guide_s1_tip": {
        "fr": "Vous pouvez changer la langue du portail à tout moment en cliquant sur les drapeaux en haut à droite.",
        "en": "You can change the portal language at any time by clicking the language buttons in the top right corner.",
    },

    # Section 2 — Steps
    "guide_s2_title": {"fr": "Les étapes de votre expédition", "en": "Your Shipment Steps"},
    "guide_step1_title": {"fr": "Remplir la packing list", "en": "Fill in the packing list"},
    "guide_step1_desc": {
        "fr": "Complétez tous les champs obligatoires (*) pour chaque lot de marchandises : informations expéditeur, nature des marchandises, dimensions et poids.",
        "en": "Complete all required fields (*) for each cargo batch: shipper information, goods description, dimensions and weight.",
    },
    "guide_step2_title": {"fr": "Soumettre pour validation", "en": "Submit for validation"},
    "guide_step2_desc": {
        "fr": "Une fois tous les champs remplis, cliquez sur « Enregistrer ». Notre équipe opérations vérifiera les informations et vous contactera si des corrections sont nécessaires.",
        "en": "Once all fields are filled, click 'Save'. Our operations team will review the information and contact you if corrections are needed.",
    },
    "guide_step3_title": {"fr": "Émission du Bill of Lading", "en": "Bill of Lading issuance"},
    "guide_step3_desc": {
        "fr": "Après validation de la packing list, le Bill of Lading (BL) est généré. Vous le retrouverez dans l'onglet Documents.",
        "en": "After packing list validation, the Bill of Lading (BL) is generated. You will find it in the Documents tab.",
    },
    "guide_step3_warning": {
        "fr": "Toute modification après émission du BL entraînera des frais d'amendement (voir section Frais).",
        "en": "Any modification after BL issuance will incur amendment fees (see Fees section).",
    },
    "guide_step4_title": {"fr": "Suivi du voyage", "en": "Voyage tracking"},
    "guide_step4_desc": {
        "fr": "Suivez la progression de votre cargaison dans l'onglet Voyage : position du navire, ETA au port de déchargement, alertes en cas de modification.",
        "en": "Track your cargo's progress in the Voyage tab: vessel position, ETA at discharge port, alerts for any changes.",
    },
    "guide_step5_title": {"fr": "Réception des marchandises", "en": "Cargo reception"},
    "guide_step5_desc": {
        "fr": "À l'arrivée au port de déchargement, vous serez notifié par email. Les documents finaux (BL original, certificat de transport à la voile) seront disponibles dans l'onglet Documents.",
        "en": "Upon arrival at the discharge port, you will be notified by email. Final documents (original BL, sailing transport certificate) will be available in the Documents tab.",
    },

    # Section 3 — Field reference
    "guide_s3_title": {"fr": "Référence des champs", "en": "Field Reference"},
    "guide_s3_intro": {
        "fr": "Voici le détail de chaque champ de la packing list. Les champs marqués * sont obligatoires.",
        "en": "Below is a detailed description of each packing list field. Fields marked * are required.",
    },
    "guide_f_customer_name_desc": {
        "fr": "Raison sociale complète du client / chargeur",
        "en": "Full legal name of the client / shipper",
    },
    "guide_f_freight_forwarder_desc": {
        "fr": "Nom du transitaire si applicable",
        "en": "Freight forwarder name if applicable",
    },
    "guide_f_code_transitaire_desc": {
        "fr": "Code interne du transitaire",
        "en": "Freight forwarder internal code",
    },
    "guide_f_shipper_name_desc": {
        "fr": "Nom complet de l'expéditeur (figurera sur le BL)",
        "en": "Full shipper name (will appear on the BL)",
    },
    "guide_f_shipper_address_desc": {
        "fr": "Adresse complète de l'expéditeur",
        "en": "Full shipper address",
    },
    "guide_f_po_number_desc": {
        "fr": "Numéro de bon de commande client",
        "en": "Client purchase order number",
    },
    "guide_f_batch_id_desc": {
        "fr": "Identifiant interne du lot",
        "en": "Internal batch identifier",
    },
    "guide_f_notify_desc": {
        "fr": "Partie à notifier à l'arrivée (nom + adresse complète). Obligatoire pour l'émission du BL.",
        "en": "Party to notify upon arrival (name + full address). Required for BL issuance.",
    },
    "guide_f_consignee_desc": {
        "fr": "Destinataire final de la marchandise (nom + adresse complète). Obligatoire pour l'émission du BL.",
        "en": "Final cargo recipient (name + full address). Required for BL issuance.",
    },
    "guide_f_pallet_type_desc": {
        "fr": "Type de palette utilisée. EPAL (80×120 cm) ou USPAL (100×120 cm) recommandé.",
        "en": "Pallet type used. EPAL (80×120 cm) or USPAL (100×120 cm) recommended.",
    },
    "guide_f_goods_desc": {
        "fr": "Nature générale des marchandises",
        "en": "General nature of goods",
    },
    "guide_f_goods_example": {
        "fr": "Vin, café, cosmétiques",
        "en": "Wine, coffee, cosmetics",
    },
    "guide_f_bio_desc": {
        "fr": "Indiquer si les produits sont certifiés biologiques",
        "en": "Indicate if products are certified organic",
    },
    "guide_f_qty_desc": {
        "fr": "Nombre total de palettes pour ce lot",
        "en": "Total number of pallets for this batch",
    },
    "guide_f_cases_desc": {
        "fr": "Nombre de caisses/cartons par palette",
        "en": "Number of cases/cartons per pallet",
    },
    "guide_f_units_desc": {
        "fr": "Nombre d'unités (bouteilles, pots…) par caisse",
        "en": "Number of units (bottles, jars…) per case",
    },
    "guide_f_imo_desc": {
        "fr": "Classe IMO si marchandises dangereuses (ex : classe 3 — liquides inflammables)",
        "en": "IMO class if dangerous goods (e.g. class 3 — flammable liquids)",
    },
    "guide_f_value_desc": {
        "fr": "Valeur déclarée de la marchandise en euros (pour assurance)",
        "en": "Declared cargo value in euros (for insurance purposes)",
    },
    "guide_f_length_desc": {
        "fr": "Longueur extérieure de la palette, emballage compris (cm)",
        "en": "Outer pallet length including packaging (cm)",
    },
    "guide_f_width_desc": {
        "fr": "Largeur extérieure de la palette, emballage compris (cm)",
        "en": "Outer pallet width including packaging (cm)",
    },
    "guide_f_height_desc": {
        "fr": "Hauteur totale du sol au sommet de la marchandise, palette incluse (cm)",
        "en": "Total height from floor to top of goods, pallet included (cm)",
    },
    "guide_f_weight_desc": {
        "fr": "Poids brut par palette : marchandise + palette + emballage (kg)",
        "en": "Gross weight per pallet: goods + pallet + wrapping (kg)",
    },
    "guide_height_warning": {
        "fr": "La hauteur maximale autorisée par palette est de 190 cm. Les palettes excédant cette hauteur seront soumises à validation par le Responsable Opérations et le Commandant lors du chargement. Des frais supplémentaires pourront être facturés.",
        "en": "Maximum allowed pallet height is 190 cm. Pallets exceeding this height will require approval from the Operations Manager and Captain during loading. Additional fees may apply.",
    },

    # Section 4 — Batches
    "guide_s4_title": {"fr": "Gestion des lots", "en": "Batch Management"},
    "guide_s4_p1": {
        "fr": "Chaque packing list peut contenir plusieurs lots (batches). Utilisez des lots séparés lorsque :",
        "en": "Each packing list can contain multiple batches. Use separate batches when:",
    },
    "guide_s4_li1": {
        "fr": "Les marchandises ont des caractéristiques différentes (nature, dimensions, poids)",
        "en": "Goods have different characteristics (type, dimensions, weight)",
    },
    "guide_s4_li2": {
        "fr": "Les destinataires (consignee/notify) sont différents",
        "en": "Recipients (consignee/notify) are different",
    },
    "guide_s4_tip": {
        "fr": "Chaque lot génère une ligne séparée sur le Bill of Lading. Regroupez les palettes identiques dans un même lot pour simplifier le BL.",
        "en": "Each batch generates a separate line on the Bill of Lading. Group identical pallets in the same batch to simplify the BL.",
    },

    # Section 5 — Packaging
    "guide_s5_title": {"fr": "Exigences d'emballage", "en": "Packaging Requirements"},
    "guide_s5_general_title": {"fr": "Règles générales", "en": "General Rules"},
    "guide_s5_li1": {
        "fr": "Les marchandises doivent être correctement emballées et filmées sur palette pour résister aux conditions de transport maritime (mouvements de roulis et tangage).",
        "en": "Goods must be properly packaged and stretch-wrapped on pallets to withstand maritime transport conditions (rolling and pitching movements).",
    },
    "guide_s5_li2": {
        "fr": "L'étiquetage doit être clairement visible sur chaque palette : référence de lot, destination, poids brut.",
        "en": "Labelling must be clearly visible on each pallet: batch reference, destination, gross weight.",
    },
    "guide_s5_pallet_title": {"fr": "Normes de palettisation", "en": "Palletisation Standards"},
    "guide_s5_pli1": {
        "fr": "Palettes EPAL (80×120 cm) ou USPAL (100×120 cm) recommandées. Autres formats sur validation préalable.",
        "en": "EPAL (80×120 cm) or USPAL (100×120 cm) pallets recommended. Other formats subject to prior approval.",
    },
    "guide_s5_pli2": {
        "fr": "Hauteur maximale recommandée : 190 cm (palette incluse). Au-delà, validation requise.",
        "en": "Maximum recommended height: 190 cm (pallet included). Above this, approval required.",
    },

    # Section 6 — Fees
    "guide_s6_title": {"fr": "Frais documentaires", "en": "Documentary Fees"},
    "guide_s6_intro": {
        "fr": "Les frais suivants s'appliquent aux services documentaires liés au Bill of Lading :",
        "en": "The following fees apply to documentary services related to the Bill of Lading:",
    },
    "guide_fee_bl": {
        "fr": "Émission du Bill of Lading (par BL)",
        "en": "Bill of Lading issuance (per BL)",
    },
    "guide_fee_amend1": {
        "fr": "Amendement avant chargement (par modification)",
        "en": "Amendment before loading (per change)",
    },
    "guide_fee_amend2": {
        "fr": "Amendement après chargement (par modification)",
        "en": "Amendment after loading (per change)",
    },
    "guide_fee_resubmit": {
        "fr": "Re-soumission après rejet (données incorrectes)",
        "en": "Re-submission after rejection (incorrect data)",
    },
    "guide_fee_urgent": {
        "fr": "Traitement urgent (< 24h avant chargement)",
        "en": "Urgent processing (< 24h before loading)",
    },
    "guide_fee_late": {
        "fr": "Soumission tardive (après deadline communiquée)",
        "en": "Late submission (after communicated deadline)",
    },
    "guide_fee_reissue": {
        "fr": "Ré-émission d'un BL (duplicata)",
        "en": "BL re-issuance (duplicate)",
    },
    "guide_fee_courier_dom": {
        "fr": "Envoi courrier BL original (France métropolitaine)",
        "en": "Original BL courier (domestic France)",
    },
    "guide_fee_courier_intl": {
        "fr": "Envoi courrier BL original (international)",
        "en": "Original BL courier (international)",
    },
    "guide_fee_manifest": {
        "fr": "Correction manifeste de cargaison (après clôture)",
        "en": "Cargo manifest correction (after closure)",
    },

    # Section 7 — US specific
    "guide_s7_title": {"fr": "Spécificités USA (AMS / ISF)", "en": "US-Specific Requirements (AMS / ISF)"},
    "guide_s7_ams": {
        "fr": "Pour toute expédition à destination des États-Unis, la déclaration AMS (Automated Manifest System) doit être soumise au moins 24 heures avant le chargement. TOWT se charge de cette déclaration à partir des données de votre packing list.",
        "en": "For all shipments to the United States, the AMS (Automated Manifest System) declaration must be submitted at least 24 hours before loading. TOWT handles this declaration based on your packing list data.",
    },
    "guide_s7_isf": {
        "fr": "L'importateur américain (ou son courtier en douane) doit déposer l'ISF (Importer Security Filing / 10+2) au plus tard 24 heures avant le chargement au port d'origine. Assurez-vous que votre importateur est informé des délais.",
        "en": "The US importer (or their customs broker) must file the ISF (Importer Security Filing / 10+2) no later than 24 hours before loading at the origin port. Ensure your importer is aware of the deadlines.",
    },
    "guide_s7_warning": {
        "fr": "Le non-respect des délais AMS/ISF peut entraîner des pénalités douanières et le refus de chargement de la marchandise.",
        "en": "Failure to comply with AMS/ISF deadlines may result in customs penalties and refusal to load the cargo.",
    },

    # Section 8 — FAQ
    "guide_s8_title": {"fr": "Questions fréquentes", "en": "Frequently Asked Questions"},
    "guide_faq1_q": {
        "fr": "Puis-je modifier ma packing list après soumission ?",
        "en": "Can I modify my packing list after submission?",
    },
    "guide_faq1_a": {
        "fr": "Oui, tant que le Bill of Lading n'a pas été émis. Après émission du BL, toute modification entraînera des frais d'amendement. Utilisez la messagerie du portail pour contacter notre équipe.",
        "en": "Yes, as long as the Bill of Lading has not been issued. After BL issuance, any modification will incur amendment fees. Use the portal messaging to contact our team.",
    },

    # Section 9 — Contact
    "guide_s9_title": {"fr": "Contact", "en": "Contact"},
    "guide_s9_p1": {
        "fr": "Pour toute question relative à votre expédition, utilisez en priorité la messagerie intégrée au portail (onglet Messages). Vous pouvez également nous contacter directement :",
        "en": "For any questions about your shipment, please use the portal messaging (Messages tab) first. You can also contact us directly:",
    },
    "guide_s9_p2": {
        "fr": "Notre équipe opérations est disponible du lundi au vendredi, 9h-18h (heure de Paris).",
        "en": "Our operations team is available Monday to Friday, 9am-6pm (Paris time).",
    },

    "cp_documents": {"fr": "Documentation", "en": "Documents", "es": "Documentación", "pt-br": "Documentação", "vi": "Tài liệu"},
    "cp_messages": {"fr": "Parlez avec nous", "en": "Contact us", "es": "Contáctenos", "pt-br": "Fale conosco", "vi": "Liên hệ"},
    "cp_about_vessel": {"fr": "À propos du", "en": "About", "es": "Sobre el", "pt-br": "Sobre o", "vi": "Giới thiệu"},
    "cp_vessel_desc_fr": {"fr": "fait partie de la flotte TOWT de voiliers-cargos modernes, conçus pour décarboner le fret maritime grâce à la propulsion vélique."},
    "cp_vessel_desc_en": {"en": "is part of the TOWT fleet of modern cargo sailing vessels, designed to decarbonize maritime freight using wind propulsion."},
    "cp_vessel_desc_es": {"es": "es parte de la flota TOWT de veleros de carga modernos, diseñados para descarbonizar el flete marítimo mediante propulsión eólica."},
    "cp_vessel_desc_ptbr": {"pt-br": "faz parte da frota TOWT de veleiros de carga modernos, projetados para descarbonizar o frete marítimo usando propulsão eólica."},
    "cp_vessel_desc_vi": {"vi": "là một phần của đội tàu buồm chở hàng hiện đại TOWT, được thiết kế để giảm carbon trong vận tải biển bằng năng lượng gió."},
    "cp_flag": {"fr": "Pavillon", "en": "Flag", "es": "Bandera", "pt-br": "Bandeira", "vi": "Cờ"},
    "cp_deadweight": {"fr": "Port en lourd", "en": "Deadweight", "es": "Peso muerto", "pt-br": "Porte bruto", "vi": "Trọng tải"},
    "cp_capacity": {"fr": "Capacité palettes", "en": "Pallet capacity", "es": "Capacidad paletas", "pt-br": "Capacidade paletes", "vi": "Sức chứa pallet"},
    "cp_speed": {"fr": "Vitesse de croisière", "en": "Cruising speed", "es": "Velocidad de crucero", "pt-br": "Velocidade de cruzeiro", "vi": "Tốc độ hành trình"},
    "cp_knots": {"fr": "nœuds", "en": "knots", "es": "nudos", "pt-br": "nós", "vi": "hải lý/giờ"},
    "cp_route": {"fr": "Trajet", "en": "Route", "es": "Ruta", "pt-br": "Rota", "vi": "Tuyến"},
    "cp_schedule": {"fr": "Calendrier", "en": "Schedule", "es": "Calendario", "pt-br": "Calendário", "vi": "Lịch trình"},
    "cp_etd": {"fr": "Départ estimé", "en": "Estimated departure", "es": "Salida estimada", "pt-br": "Partida estimada", "vi": "Khởi hành dự kiến"},
    "cp_eta": {"fr": "Arrivée estimée", "en": "Estimated arrival", "es": "Llegada estimada", "pt-br": "Chegada estimada", "vi": "Đến dự kiến"},
    "cp_atd": {"fr": "Départ réel", "en": "Actual departure", "es": "Salida real", "pt-br": "Partida real", "vi": "Khởi hành thực tế"},
    "cp_ata": {"fr": "Arrivée réelle", "en": "Actual arrival", "es": "Llegada real", "pt-br": "Chegada real", "vi": "Đến thực tế"},
    "cp_distance": {"fr": "Distance", "en": "Distance", "es": "Distancia", "pt-br": "Distância", "vi": "Khoảng cách"},
    "cp_crew": {"fr": "Équipage embarqué", "en": "Crew on board", "es": "Tripulación a bordo", "pt-br": "Tripulação a bordo", "vi": "Thủy thủ đoàn"},
    "cp_leg_code": {"fr": "Code leg", "en": "Leg code", "es": "Código tramo", "pt-br": "Código trecho", "vi": "Mã chặng"},
    "cp_contractual_docs": {"fr": "Documentation contractuelle", "en": "Contractual documents", "es": "Documentación contractual", "pt-br": "Documentação contratual", "vi": "Tài liệu hợp đồng"},
    "cp_terms_title": {"fr": "Conditions générales de transport", "en": "General conditions of transport", "es": "Condiciones generales de transporte", "pt-br": "Condições gerais de transporte", "vi": "Điều kiện vận chuyển chung"},
    "cp_conversation": {"fr": "Fil de discussion", "en": "Conversation", "es": "Conversación", "pt-br": "Conversa", "vi": "Cuộc trò chuyện"},
    "cp_no_messages": {"fr": "Aucun message pour l'instant. Envoyez un message pour démarrer la conversation !", "en": "No messages yet. Send a message to start the conversation!", "es": "No hay mensajes todavía. ¡Envíe un mensaje para iniciar la conversación!", "pt-br": "Nenhuma mensagem ainda. Envie uma mensagem para iniciar a conversa!", "vi": "Chưa có tin nhắn. Gửi tin nhắn để bắt đầu cuộc trò chuyện!"},
    "cp_write_msg": {"fr": "Écrivez votre message…", "en": "Write your message…", "es": "Escriba su mensaje…", "pt-br": "Escreva sua mensagem…", "vi": "Viết tin nhắn…"},
    "cp_send": {"fr": "Envoyer", "en": "Send", "es": "Enviar", "pt-br": "Enviar", "vi": "Gửi"},
    "cp_contact_email": {"fr": "Pour les urgences, contactez-nous à", "en": "For urgent matters, contact us at", "es": "Para asuntos urgentes, contáctenos en", "pt-br": "Para assuntos urgentes, entre em contato em", "vi": "Trường hợp khẩn cấp, liên hệ"},
    "cp_delete_batch_confirm": {"fr": "Supprimer ce batch ?", "en": "Delete this batch?", "es": "¿Eliminar este lote?", "pt-br": "Excluir este lote?", "vi": "Xóa lô hàng này?"},
    "cp_no_voyage_info": {"fr": "Aucune information de voyage disponible pour le moment.", "en": "No voyage information available yet.", "es": "No hay información de viaje disponible todavía.", "pt-br": "Nenhuma informação de viagem disponível no momento.", "vi": "Chưa có thông tin chuyến đi."},
    "cp_original_planning": {"fr": "Planification d'origine", "en": "Original planning", "es": "Planificación original", "pt-br": "Planejamento original", "vi": "Kế hoạch ban đầu"},
    "cp_updated_schedule": {"fr": "Actualisation", "en": "Updated schedule", "es": "Actualización", "pt-br": "Atualização", "vi": "Cập nhật"},
    "cp_actual_times": {"fr": "Réalisation", "en": "Actual times", "es": "Realización", "pt-br": "Realização", "vi": "Thực tế"},
    "cp_etd_ref": {"fr": "ETD de référence", "en": "Reference ETD", "es": "ETD de referencia", "pt-br": "ETD de referência", "vi": "ETD tham chiếu"},
    "cp_eta_ref": {"fr": "ETA de référence", "en": "Reference ETA", "es": "ETA de referencia", "pt-br": "ETA de referência", "vi": "ETA tham chiếu"},
    "cp_vessel_position": {"fr": "Position du navire", "en": "Vessel position", "es": "Posición del buque", "pt-br": "Posição do navio", "vi": "Vị trí tàu"},
    "cp_vessel_in_transit": {"fr": "En navigation", "en": "In transit", "es": "En tránsito", "pt-br": "Em trânsito", "vi": "Đang di chuyển"},
    "cp_notif_new_schedule": {"fr": "Nouveau calendrier", "en": "New schedule", "es": "Nuevo calendario", "pt-br": "Novo calendário", "vi": "Lịch trình mới"},
    "cp_notif_eta_change": {"fr": "Modification ETA", "en": "ETA change", "es": "Cambio ETA", "pt-br": "Alteração ETA", "vi": "Thay đổi ETA"},
    "cp_notif_departed": {"fr": "Le navire a quitté son port d'origine", "en": "The vessel has departed from origin port", "es": "El buque ha zarpado del puerto de origen", "pt-br": "O navio partiu do porto de origem", "vi": "Tàu đã rời cảng xuất phát"},
    "cp_notif_arrived": {"fr": "Le navire est arrivé à destination", "en": "The vessel has arrived at destination", "es": "El buque ha llegado a destino", "pt-br": "O navio chegou ao destino", "vi": "Tàu đã đến đích"},
    "cp_notif_new_message": {"fr": "Nouveau message de la compagnie", "en": "New message from the company", "es": "Nuevo mensaje de la compañía", "pt-br": "Nova mensagem da empresa", "vi": "Tin nhắn mới từ công ty"},
    "cp_full_itinerary": {"fr": "Itinéraire complet", "en": "Full itinerary", "es": "Itinerario completo", "pt-br": "Itinerário completo", "vi": "Lịch trình đầy đủ"},
    "cp_position_soon": {"fr": "Position bientôt disponible", "en": "Position available soon", "es": "Posición disponible pronto", "pt-br": "Posição disponível em breve", "vi": "Vị trí sẽ sớm có"},
    "cp_your_cargo": {"fr": "Votre cargo à bord", "en": "Your cargo on board", "es": "Su carga a bordo", "pt-br": "Sua carga a bordo", "vi": "Hàng hóa của bạn trên tàu"},
    # ═══ BACKOFFICE — QUICK ACCESS CARDS ═══
    "qa_planning_title": {"fr": "Planification", "en": "Planning", "es": "Planificación", "pt-br": "Planejamento", "vi": "Kế hoạch"},
    "qa_planning_desc": {"fr": "Routes, escales, planning", "en": "Routes, port calls, planning", "es": "Rutas, escalas, planificación", "pt-br": "Rotas, escalas, planejamento", "vi": "Tuyến, cảng, kế hoạch"},
    "qa_commercial_title": {"fr": "Commercial", "en": "Commercial", "es": "Comercial", "pt-br": "Comercial", "vi": "Thương mại"},
    "qa_commercial_desc": {"fr": "Commandes, affectations", "en": "Orders, assignments", "es": "Pedidos, asignaciones", "pt-br": "Pedidos, atribuições", "vi": "Đơn hàng, phân bổ"},
    "qa_escale_title": {"fr": "Escale", "en": "Port call", "es": "Escala", "pt-br": "Escala", "vi": "Ghé cảng"},
    "qa_escale_desc": {"fr": "Opérations portuaires", "en": "Port operations", "es": "Operaciones portuarias", "pt-br": "Operações portuárias", "vi": "Hoạt động cảng"},
    "qa_finance_title": {"fr": "Finances", "en": "Finance", "es": "Finanzas", "pt-br": "Finanças", "vi": "Tài chính"},
    "qa_finance_desc": {"fr": "Revenus, dépenses, marges", "en": "Revenue, expenses, margins", "es": "Ingresos, gastos, márgenes", "pt-br": "Receitas, despesas, margens", "vi": "Thu, chi, lợi nhuận"},

    "cp_key_features": {"fr": "Caractéristiques principales", "en": "Key features", "es": "Características principales", "pt-br": "Características principais", "vi": "Đặc điểm chính"},

    # ═══ CO2 / MRV / DECARBONATION (NEW) ═══
    "co2_decarbonation": {"fr": "Décarbonation", "en": "Decarbonation", "es": "Descarbonización", "pt-br": "Descarbonização", "vi": "Giảm carbon"},
    "co2_for_shipment": {"fr": "Décarbonation pour cette expédition — Transport à la voile vs conventionnel",
                         "en": "Decarbonation for this shipment — Sailing vs conventional transport",
                         "es": "Descarbonización para este envío — Transporte a vela vs convencional",
                         "pt-br": "Descarbonização para esta remessa — Transporte à vela vs convencional",
                         "vi": "Giảm carbon cho lô hàng này — Vận tải buồm so với thông thường"},
    "co2_avoided_tonnes": {"fr": "tonnes CO₂ décarbonées", "en": "tonnes CO₂ decarbonized",
                           "es": "toneladas CO₂ descarbonizadas", "pt-br": "toneladas CO₂ descarbonizadas",
                           "vi": "tấn CO₂ giảm"},
    "nav_mrv": {"fr": "MRV Fuel", "en": "MRV Fuel", "es": "MRV Combustible", "pt-br": "MRV Combustível", "vi": "MRV Nhiên liệu"},

    # MRV page titles & buttons
    "mrv_title": {"fr": "MRV — Rapport carburant", "en": "MRV — Fuel Reporting", "es": "MRV — Informe combustible", "pt-br": "MRV — Relatório combustível", "vi": "MRV — Báo cáo nhiên liệu"},
    "mrv_export_dnv": {"fr": "Export DNV CSV", "en": "Export DNV CSV", "es": "Exportar DNV CSV", "pt-br": "Exportar DNV CSV", "vi": "Xuất DNV CSV"},
    "mrv_carbon_report": {"fr": "Rapport carbone", "en": "Carbon Report", "es": "Informe carbono", "pt-br": "Relatório carbono", "vi": "Báo cáo carbon"},
    "mrv_recalculate": {"fr": "Recalculer", "en": "Recalculate", "es": "Recalcular", "pt-br": "Recalcular", "vi": "Tính lại"},

    # MRV summary cards
    "mrv_total_consumption": {"fr": "Consommation MDO totale", "en": "Total MDO Consumption", "es": "Consumo MDO total", "pt-br": "Consumo MDO total", "vi": "Tổng tiêu thụ MDO"},
    "mrv_total_co2": {"fr": "Émissions CO₂ totales", "en": "Total CO₂ Emissions", "es": "Emisiones CO₂ totales", "pt-br": "Emissões CO₂ totais", "vi": "Tổng phát thải CO₂"},
    "mrv_events_count": {"fr": "Événements MRV", "en": "MRV Events", "es": "Eventos MRV", "pt-br": "Eventos MRV", "vi": "Sự kiện MRV"},
    "mrv_data_quality": {"fr": "Qualité des données", "en": "Data Quality", "es": "Calidad de datos", "pt-br": "Qualidade dos dados", "vi": "Chất lượng dữ liệu"},
    "mrv_errors": {"fr": "Erreurs", "en": "Errors", "es": "Errores", "pt-br": "Erros", "vi": "Lỗi"},
    "mrv_warnings": {"fr": "Alertes", "en": "Warnings", "es": "Alertas", "pt-br": "Alertas", "vi": "Cảnh báo"},
    "mrv_no_data": {"fr": "Aucune donnée", "en": "No data", "es": "Sin datos", "pt-br": "Sem dados", "vi": "Không có dữ liệu"},

    # MRV table headers
    "mrv_leg": {"fr": "Leg", "en": "Leg", "es": "Tramo", "pt-br": "Trecho", "vi": "Chặng"},
    "mrv_route": {"fr": "Route", "en": "Route", "es": "Ruta", "pt-br": "Rota", "vi": "Tuyến"},
    "mrv_consumption_mt": {"fr": "Consommation (mt)", "en": "Consumption (mt)", "es": "Consumo (mt)", "pt-br": "Consumo (mt)", "vi": "Tiêu thụ (mt)"},
    "mrv_co2_mt": {"fr": "CO₂ (mt)", "en": "CO₂ (mt)", "es": "CO₂ (mt)", "pt-br": "CO₂ (mt)", "vi": "CO₂ (mt)"},
    "mrv_quality": {"fr": "Qualité", "en": "Quality", "es": "Calidad", "pt-br": "Qualidade", "vi": "Chất lượng"},
    "mrv_view": {"fr": "Voir", "en": "View", "es": "Ver", "pt-br": "Ver", "vi": "Xem"},
    "mrv_no_legs": {"fr": "Aucun leg pour", "en": "No legs for", "es": "Sin tramos para", "pt-br": "Nenhum trecho para", "vi": "Không có chặng cho"},
    "mrv_in": {"fr": "en", "en": "in", "es": "en", "pt-br": "em", "vi": "trong"},

    # MRV parameters
    "mrv_parameters": {"fr": "Paramètres MRV", "en": "MRV Parameters", "es": "Parámetros MRV", "pt-br": "Parâmetros MRV", "vi": "Tham số MRV"},
    "mrv_avg_density": {"fr": "Densité moyenne MDO (t/m³)", "en": "Avg MDO Density (t/m³)", "es": "Densidad MDO promedio (t/m³)", "pt-br": "Densidade MDO média (t/m³)", "vi": "Mật độ MDO trung bình (t/m³)"},
    "mrv_deviation": {"fr": "Déviation admissible MDO (mt)", "en": "MDO Admissible Deviation (mt)", "es": "Desviación admisible MDO (mt)", "pt-br": "Desvio admissível MDO (mt)", "vi": "Sai lệch cho phép MDO (mt)"},
    "mrv_co2_factor": {"fr": "Facteur émission CO₂ (t CO₂/t fuel)", "en": "CO₂ Emission Factor (t CO₂/t fuel)", "es": "Factor emisión CO₂ (t CO₂/t fuel)", "pt-br": "Fator emissão CO₂ (t CO₂/t fuel)", "vi": "Hệ số phát thải CO₂ (t CO₂/t fuel)"},
    "mrv_save_params": {"fr": "Enregistrer les paramètres", "en": "Save Parameters", "es": "Guardar parámetros", "pt-br": "Salvar parâmetros", "vi": "Lưu tham số"},

    # MRV leg detail
    "mrv_quality_summary": {"fr": "Résumé qualité", "en": "Quality Summary", "es": "Resumen calidad", "pt-br": "Resumo qualidade", "vi": "Tóm tắt chất lượng"},
    "mrv_pending": {"fr": "En attente", "en": "Pending", "es": "Pendiente", "pt-br": "Pendente", "vi": "Đang chờ"},
    "mrv_co2_factor_label": {"fr": "Facteur CO₂", "en": "CO₂ Factor", "es": "Factor CO₂", "pt-br": "Fator CO₂", "vi": "Hệ số CO₂"},
    "mrv_density_label": {"fr": "Densité MDO", "en": "MDO Density", "es": "Densidad MDO", "pt-br": "Densidade MDO", "vi": "Mật độ MDO"},
    "mrv_admissible_deviation": {"fr": "Déviation admissible", "en": "Admissible Deviation", "es": "Desviación admisible", "pt-br": "Desvio admissível", "vi": "Sai lệch cho phép"},
    "mrv_total_consumption_label": {"fr": "Consommation totale", "en": "Total Consumption", "es": "Consumo total", "pt-br": "Consumo total", "vi": "Tổng tiêu thụ"},
    "mrv_co2_emissions": {"fr": "Émissions CO₂", "en": "CO₂ Emissions", "es": "Emisiones CO₂", "pt-br": "Emissões CO₂", "vi": "Phát thải CO₂"},

    # MRV SOF suggestions
    "mrv_sof_suggestions": {"fr": "Événements SOF à lier comme événements MRV", "en": "SOF Events to link as MRV events", "es": "Eventos SOF para vincular como eventos MRV", "pt-br": "Eventos SOF para vincular como eventos MRV", "vi": "Sự kiện SOF để liên kết thành sự kiện MRV"},
    "mrv_no_events": {"fr": "Aucun événement MRV enregistré pour ce leg.", "en": "No MRV events recorded for this leg yet.", "es": "No hay eventos MRV para este tramo.", "pt-br": "Nenhum evento MRV para este trecho.", "vi": "Chưa có sự kiện MRV cho chặng này."},
    "mrv_use_sof": {"fr": "Utilisez les suggestions SOF ci-dessus pour commencer.", "en": "Use the SOF event suggestions above to get started.", "es": "Use las sugerencias SOF para comenzar.", "pt-br": "Use as sugestões SOF acima para começar.", "vi": "Sử dụng các gợi ý SOF ở trên để bắt đầu."},

    # MRV event form
    "mrv_add_event": {"fr": "Ajouter un événement MRV", "en": "Add MRV Event", "es": "Añadir evento MRV", "pt-br": "Adicionar evento MRV", "vi": "Thêm sự kiện MRV"},
    "mrv_edit_event": {"fr": "Modifier l'événement MRV", "en": "Edit MRV Event", "es": "Editar evento MRV", "pt-br": "Editar evento MRV", "vi": "Sửa sự kiện MRV"},
    "mrv_event_info": {"fr": "Informations événement", "en": "Event Information", "es": "Información del evento", "pt-br": "Informações do evento", "vi": "Thông tin sự kiện"},
    "mrv_event_type": {"fr": "Type d'événement", "en": "Event Type", "es": "Tipo de evento", "pt-br": "Tipo de evento", "vi": "Loại sự kiện"},
    "mrv_date_utc": {"fr": "Date UTC", "en": "Date UTC", "es": "Fecha UTC", "pt-br": "Data UTC", "vi": "Ngày UTC"},
    "mrv_time_utc": {"fr": "Heure UTC", "en": "Time UTC", "es": "Hora UTC", "pt-br": "Hora UTC", "vi": "Giờ UTC"},
    "mrv_distance_prev": {"fr": "Distance du précéd. (NM)", "en": "Distance from prev. (NM)", "es": "Distancia del anterior (NM)", "pt-br": "Distância do anterior (NM)", "vi": "Khoảng cách từ trước (NM)"},

    # MRV DO counters
    "mrv_do_counters": {"fr": "Compteurs DO (totaux cumulés)", "en": "DO Counters (running totals)", "es": "Contadores DO (totales acumulados)", "pt-br": "Contadores DO (totais acumulados)", "vi": "Bộ đếm DO (tổng cộng dồn)"},
    "mrv_port_me": {"fr": "Moteur principal bâbord", "en": "Port Main Engine", "es": "Motor principal babor", "pt-br": "Motor principal bombordo", "vi": "Máy chính mạn trái"},
    "mrv_stbd_me": {"fr": "Moteur principal tribord", "en": "Starboard Main Engine", "es": "Motor principal estribor", "pt-br": "Motor principal estibordo", "vi": "Máy chính mạn phải"},
    "mrv_fwd_gen": {"fr": "Générateur avant", "en": "FWD Generator", "es": "Generador proa", "pt-br": "Gerador proa", "vi": "Máy phát phía trước"},
    "mrv_aft_gen": {"fr": "Générateur arrière", "en": "AFT Generator", "es": "Generador popa", "pt-br": "Gerador popa", "vi": "Máy phát phía sau"},

    # MRV fuel & cargo
    "mrv_fuel_cargo": {"fr": "Carburant & cargaison", "en": "Fuel & Cargo", "es": "Combustible y carga", "pt-br": "Combustível e carga", "vi": "Nhiên liệu & hàng hóa"},
    "mrv_rob": {"fr": "ROB déclaré (mt)", "en": "ROB Declared (mt)", "es": "ROB declarado (mt)", "pt-br": "ROB declarado (mt)", "vi": "ROB khai báo (mt)"},
    "mrv_cargo": {"fr": "Cargo MRV (mt)", "en": "Cargo MRV (mt)", "es": "Carga MRV (mt)", "pt-br": "Carga MRV (mt)", "vi": "Hàng MRV (mt)"},
    "mrv_bunkering_qty": {"fr": "Quantité soutage (mt)", "en": "Bunkering Qty (mt)", "es": "Cantidad búnker (mt)", "pt-br": "Qtd abastecimento (mt)", "vi": "Lượng tiếp nhiên liệu (mt)"},
    "mrv_bunkering_date": {"fr": "Date de soutage", "en": "Bunkering Date", "es": "Fecha búnker", "pt-br": "Data abastecimento", "vi": "Ngày tiếp nhiên liệu"},

    # MRV position
    "mrv_position": {"fr": "Position (depuis AIS/GPS)", "en": "Position (from AIS/GPS)", "es": "Posición (desde AIS/GPS)", "pt-br": "Posição (de AIS/GPS)", "vi": "Vị trí (từ AIS/GPS)"},
    "mrv_lat_deg": {"fr": "Lat degrés", "en": "Lat Degrees", "es": "Lat grados", "pt-br": "Lat graus", "vi": "Vĩ độ"},
    "mrv_lat_min": {"fr": "Lat minutes", "en": "Lat Minutes", "es": "Lat minutos", "pt-br": "Lat minutos", "vi": "Phút vĩ độ"},
    "mrv_lon_deg": {"fr": "Lon degrés", "en": "Lon Degrees", "es": "Lon grados", "pt-br": "Lon graus", "vi": "Kinh độ"},
    "mrv_lon_min": {"fr": "Lon minutes", "en": "Lon Minutes", "es": "Lon minutos", "pt-br": "Lon minutos", "vi": "Phút kinh độ"},

    # MRV table column headers (leg detail)
    "mrv_me_cons": {"fr": "Cons. ME", "en": "ME Cons.", "es": "Cons. MP", "pt-br": "Cons. MP", "vi": "Tiêu thụ MC"},
    "mrv_ae_cons": {"fr": "Cons. AE", "en": "AE Cons.", "es": "Cons. MA", "pt-br": "Cons. MA", "vi": "Tiêu thụ MP"},
    "mrv_total": {"fr": "Total", "en": "Total", "es": "Total", "pt-br": "Total", "vi": "Tổng"},
    "mrv_rob_calc": {"fr": "ROB calc.", "en": "ROB Calc.", "es": "ROB calc.", "pt-br": "ROB calc.", "vi": "ROB tính"},
    "mrv_dist_nm": {"fr": "Dist (NM)", "en": "Dist (NM)", "es": "Dist (NM)", "pt-br": "Dist (NM)", "vi": "KC (NM)"},
    "mrv_event": {"fr": "Événement", "en": "Event", "es": "Evento", "pt-br": "Evento", "vi": "Sự kiện"},
    "mrv_confirm_delete": {"fr": "Supprimer cet événement MRV ?", "en": "Delete this MRV event?", "es": "¿Eliminar este evento MRV?", "pt-br": "Excluir este evento MRV?", "vi": "Xóa sự kiện MRV này?"},

    # MRV event types (translated labels)
    "mrv_type_departure": {"fr": "Départ", "en": "Departure", "es": "Salida", "pt-br": "Partida", "vi": "Khởi hành"},
    "mrv_type_arrival": {"fr": "Arrivée", "en": "Arrival", "es": "Llegada", "pt-br": "Chegada", "vi": "Đến nơi"},
    "mrv_type_at_sea": {"fr": "En mer", "en": "At Sea", "es": "En el mar", "pt-br": "No mar", "vi": "Trên biển"},
    "mrv_type_begin_anchoring": {"fr": "Mouillage / À quai", "en": "Begin Anchoring/Drifting", "es": "Fondeo / En muelle", "pt-br": "Fundeio / Atracado", "vi": "Bắt đầu neo"},
    "mrv_type_end_anchoring": {"fr": "Fin de mouillage", "en": "End Anchoring/Drifting", "es": "Fin fondeo", "pt-br": "Fim fundeio", "vi": "Kết thúc neo"},

    # ═══ CARGO FORM / EXCEL (NEW) ═══
    "error_no_file": {"fr": "Aucun fichier sélectionné.", "en": "No file selected.",
                      "es": "Ningún archivo seleccionado.", "pt-br": "Nenhum arquivo selecionado.",
                      "vi": "Chưa chọn tệp nào."},
    "error_invalid_file": {"fr": "Fichier Excel invalide. Veuillez utiliser le template TOWT.",
                           "en": "Invalid Excel file. Please use the TOWT template.",
                           "es": "Archivo Excel no válido. Utilice la plantilla TOWT.",
                           "pt-br": "Arquivo Excel inválido. Use o modelo TOWT.",
                           "vi": "Tệp Excel không hợp lệ. Vui lòng sử dụng mẫu TOWT."},
    "error_invalid_format": {"fr": "Format invalide. Veuillez utiliser le template Packing List TOWT.",
                             "en": "Invalid format. Please use the TOWT Packing List template.",
                             "es": "Formato no válido. Utilice la plantilla TOWT.",
                             "pt-br": "Formato inválido. Use o modelo de Packing List TOWT.",
                             "vi": "Định dạng không hợp lệ. Vui lòng sử dụng mẫu Packing List TOWT."},
    "download_template": {"fr": "Télécharger template Excel", "en": "Download Excel template",
                          "es": "Descargar plantilla Excel", "pt-br": "Baixar modelo Excel",
                          "vi": "Tải mẫu Excel"},
    "import_excel": {"fr": "Importer Excel", "en": "Import Excel", "es": "Importar Excel", "pt-br": "Importar Excel", "vi": "Nhập Excel"},
    "import_excel_title": {"fr": "Importer le template Excel", "en": "Import Excel Template",
                           "es": "Importar plantilla Excel", "pt-br": "Importar modelo Excel",
                           "vi": "Nhập mẫu Excel"},
    "import_excel_desc": {"fr": "Envoyez votre template Packing List rempli. Les données seront mises à jour.",
                          "en": "Upload your filled Packing List template. Existing batch data will be updated.",
                          "es": "Suba su plantilla de Packing List completada. Los datos se actualizarán.",
                          "pt-br": "Envie seu modelo de Packing List preenchido. Os dados serão atualizados.",
                          "vi": "Tải lên mẫu Packing List đã điền. Dữ liệu lô hàng sẽ được cập nhật."},
    "confirm_delete_batch": {"fr": "Supprimer ce batch ?", "en": "Delete this batch?",
                             "es": "¿Eliminar este lote?", "pt-br": "Excluir este lote?",
                             "vi": "Xóa lô hàng này?"},

    # ═══ STRUCTURED ADDRESS FIELDS (NEW) ═══
    "f_description_of_goods": {"fr": "Description des marchandises", "en": "Description of the goods",
                               "es": "Descripción de las mercancías", "pt-br": "Descrição das mercadorias",
                               "vi": "Mô tả hàng hóa"},
    "f_address": {"fr": "Adresse", "en": "Address", "es": "Dirección", "pt-br": "Endereço", "vi": "Địa chỉ"},
    "f_postal_code": {"fr": "Code postal", "en": "Postal code", "es": "Código postal", "pt-br": "CEP", "vi": "Mã bưu chính"},
    "f_city": {"fr": "Ville", "en": "City", "es": "Ciudad", "pt-br": "Cidade", "vi": "Thành phố"},
    "f_country": {"fr": "Pays", "en": "Country", "es": "País", "pt-br": "País", "vi": "Quốc gia"},
    "f_name": {"fr": "Nom", "en": "Name", "es": "Nombre", "pt-br": "Nome", "vi": "Tên"},
    "f_notify_party": {"fr": "Notify Party", "en": "Notify Party", "es": "Parte notificada", "pt-br": "Parte notificada", "vi": "Bên thông báo"},
    "f_consignee": {"fr": "Consignee (Destinataire)", "en": "Consignee", "es": "Consignatario", "pt-br": "Consignatário", "vi": "Người nhận hàng"},
    "f_shipper": {"fr": "Shipper (Expéditeur)", "en": "Shipper", "es": "Expedidor", "pt-br": "Embarcador", "vi": "Người gửi hàng"},
    "nav_onboard": {"fr": "On Board", "en": "On Board", "es": "A bordo", "pt-br": "A bordo", "vi": "Trên tàu"},
}


def t(key: str, lang: str = DEFAULT_LANG) -> str:
    """Get translation for a key in the given language."""
    entry = TRANSLATIONS.get(key)
    if not entry:
        return key
    return entry.get(lang) or entry.get(DEFAULT_LANG) or key


def get_t(lang: str = DEFAULT_LANG):
    """Return a translation function bound to a language."""
    def _t(key: str) -> str:
        return t(key, lang)
    return _t


def get_lang_from_request(request, user=None) -> str:
    """Determine language from user preference, query param, or cookie."""
    # 1. Query param ?lang=xx
    lang = None
    if hasattr(request, 'query_params'):
        lang = request.query_params.get('lang')
    # 2. User preference
    if not lang and user and hasattr(user, 'language') and user.language:
        lang = user.language
    # 3. Cookie
    if not lang:
        lang = request.cookies.get('towt_lang')
    # 4. Default
    if not lang or lang not in SUPPORTED_LANGUAGES:
        lang = DEFAULT_LANG
    return lang
