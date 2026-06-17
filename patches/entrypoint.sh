#!/bin/bash
# MiroFish Neo4j Fork — Auto-patch entrypoint
# Applies all Neo4j patches before starting MiroFish

echo "=== Applying Neo4j patches ==="

# 1. Install neo4j driver in the backend venv
cd /app/backend && uv pip install neo4j 2>/dev/null

# 2. Replace graph_builder.py with Neo4j version
cp /patches/neo4j_graph_builder.py /app/backend/app/services/graph_builder.py
echo "✅ graph_builder.py patched"

# 3. Replace zep_entity_reader.py with Neo4j version
cp /patches/neo4j_entity_reader.py /app/backend/app/services/zep_entity_reader.py
echo "✅ zep_entity_reader.py patched"

# 4. Copy patch_zep_tools.py into the services directory
cp /patches/patch_zep_tools.py /app/backend/app/services/patch_zep_tools.py
echo "✅ patch_zep_tools.py copied"

# 5. Copy neo4j_graph_api.py blueprint
cp /patches/neo4j_graph_api.py /app/backend/app/api/neo4j_graph.py
echo "✅ neo4j_graph_api.py copied"

# 6. Patch config.py — skip ZEP_API_KEY validation
python3 -c "
fp = '/app/backend/app/config.py'
with open(fp, 'r') as f:
    c = f.read()
if 'ZEP replaced by Neo4j' not in c:
    c = c.replace(
        'if not cls.ZEP_API_KEY:',
        'if False:  # ZEP replaced by Neo4j  # if not cls.ZEP_API_KEY:'
    )
    with open(fp, 'w') as f:
        f.write(c)
    print('✅ config.py patched')
else:
    print('✅ config.py already patched')
"

# 7. Patch graph.py — remove ZEP_API_KEY checks
python3 -c "
fp = '/app/backend/app/api/graph.py'
with open(fp, 'r') as f:
    c = f.read()

c = c.replace(
    '''        errors = []
        if not Config.ZEP_API_KEY:
            errors.append(\"ZEP_API_KEY未配置\")
        if errors:
            logger.error(f\"配置错误: {errors}\")
            return jsonify({
                \"success\": False,
                \"error\": \"配置缺失: \" + \"; \".join(errors)
            }), 500''',
    '        errors = []'
)

c = c.replace(
    '''        errors = []
        if not Config.ZEP_API_KEY:
            errors.append(t('api.zepApiKeyMissing'))
        if errors:
            logger.error(f\"配置错误: {errors}\")
            return jsonify({
                \"success\": False,
                \"error\": t('api.configError', details=\"; \".join(errors))
            }), 500''',
    '        errors = []'
)

for old_check in [
    '''        if not Config.ZEP_API_KEY:
            return jsonify({
                \"success\": False,
                \"error\": t('api.zepApiKeyMissing')
            }), 500''',
    '''        if not Config.ZEP_API_KEY:
            return jsonify({
                \"success\": False,
                \"error\": \"ZEP_API_KEY未配置\"
            }), 500'''
]:
    c = c.replace(old_check, '        pass  # Neo4j - no API key needed')

with open(fp, 'w') as f:
    f.write(c)
print('✅ graph.py patched')
"

# 8. Patch run.py — register Neo4j blueprint + apply zep_tools monkey-patch
python3 -c "
fp = '/app/backend/run.py'
with open(fp, 'r') as f:
    c = f.read()

# Add Neo4j blueprint registration
if 'neo4j_bp' not in c:
    c = c.replace(
        \"app.register_blueprint(graph_bp, url_prefix='/api/graph')\",
        \"\"\"app.register_blueprint(graph_bp, url_prefix='/api/graph')
    # Neo4j Local Graph API
    try:
        from app.api.neo4j_graph import neo4j_bp
        app.register_blueprint(neo4j_bp, url_prefix='/api/neo4j')
        print('Neo4j graph API registered at /api/neo4j/')
    except Exception as e:
        print(f'Neo4j blueprint not loaded: {e}')\"\"\"
    )
    print('✅ run.py: Neo4j blueprint registered')

# Add zep_tools monkey-patch
if 'patch_zep_tools' not in c:
    c = c.replace(
        'app = create_app()',
        \"\"\"app = create_app()
    # Apply Neo4j monkey-patches to ZepToolsService
    try:
        from app.services.patch_zep_tools import patch_zep_tools
        patch_zep_tools()
        print('Neo4j: ZepToolsService monkey-patched')
    except Exception as e:
        print(f'Neo4j zep_tools patch not applied: {e}')\"\"\"
    )
    print('✅ run.py: zep_tools monkey-patch added')

with open(fp, 'w') as f:
    f.write(c)
"

echo "=== All patches applied ==="

# Start MiroFish normally
exec npm run dev
