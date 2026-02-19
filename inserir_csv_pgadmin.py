import psycopg2
import pandas as pd
import traceback

# Conectar ao banco de dados
try:
    conn = psycopg2.connect(
        host="localhost",
        database="teste",
        user="postgres",
        password="123mudar"
    )
    print("✅ Conexão com o banco de dados estabelecida com sucesso!")
except Exception as e:
    print(f"❌ Erro de conexão: {e}")
    exit(1)

# Ler o arquivo CSV
try:
    df = pd.read_csv('Escolas_Juazeiro_BA.csv', encoding='utf-8', sep=';')
    print(f"✅ CSV lido com sucesso. Total de linhas: {len(df)}")
    print(f"   Colunas: {list(df.columns)}")
except Exception as e:
    print(f"❌ Erro ao ler CSV: {e}")
    exit(1)

# Verificar se o DataFrame tem dados
print(f"\n📊 Primeiras 3 linhas do CSV:")
print(df.head(3))

cursor = conn.cursor()

# 1. Primeiro, verificar se a tabela já existe e tem dados
cursor.execute("""
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_name = 'escola'
    )
""")
tabela_existe = cursor.fetchone()[0]

if tabela_existe:
    print("✅ Tabela 'escola' já existe no banco de dados")
    
    # Verificar se há dados na tabela
    cursor.execute("SELECT COUNT(*) FROM escola")
    count_antes = cursor.fetchone()[0]
    print(f"   A tabela atualmente tem {count_antes} registros")
else:
    print("ℹ️  Tabela 'escola' não existe. Será criada.")

# 2. Criar tabela (se não existir)
cursor.execute("""
    CREATE TABLE IF NOT EXISTS escola (
        id INTEGER PRIMARY KEY,
        inep VARCHAR(20),
        escola VARCHAR(200) NOT NULL,
        endereco VARCHAR(200),
        bairro VARCHAR(100),
        distrito VARCHAR(100),
        gestor VARCHAR(100),
        telefone_extraido VARCHAR(20),
        localidade_id INTEGER
    )
""")
print("✅ Tabela 'escola' verificada/criada")

# 3. Verificar estrutura da tabela
cursor.execute("""
    SELECT column_name, data_type, is_nullable 
    FROM information_schema.columns 
    WHERE table_name = 'escola' 
    ORDER BY ordinal_position
""")
colunas_tabela = cursor.fetchall()
print(f"\n📋 Estrutura da tabela 'escola':")
for col in colunas_tabela:
    print(f"   {col[0]} ({col[1]}) - Nullable: {col[2]}")

# 4. Preparar dados para inserção
print(f"\n🔄 Preparando dados para inserção...")
dados_para_inserir = []

for idx, row in df.iterrows():
    try:
        # Garantir que todos os campos sejam strings (exceto id e localidade_id)
        id_val = int(row['id']) if pd.notna(row['id']) else None
        escola_val = str(row['escola']).strip() if pd.notna(row['escola']) else ''
        
        # Se o nome da escola está vazio, pular
        if not escola_val:
            print(f"⚠️  Linha {idx+1}: Escola sem nome, pulando...")
            continue
            
        dados_para_inserir.append((
            id_val,
            str(row['inep']).strip() if pd.notna(row['inep']) else None,
            escola_val,
            str(row['endereco']).strip() if pd.notna(row['endereco']) else None,
            str(row['bairro']).strip() if pd.notna(row['bairro']) else None,
            str(row['distrito']).strip() if pd.notna(row['distrito']) else None,
            str(row['gestor']).strip() if pd.notna(row['gestor']) else None,
            str(row['telefone_extraido']).strip() if pd.notna(row['telefone_extraido']) else None,
            int(row['localidade_id']) if pd.notna(row['localidade_id']) else None
        ))
        
    except Exception as e:
        print(f"⚠️  Erro na linha {idx+1}: {e}")
        print(f"   Dados da linha: {row.to_dict()}")

print(f"✅ Preparados {len(dados_para_inserir)} registros para inserção")

if not dados_para_inserir:
    print("❌ Nenhum dado válido para inserir!")
    conn.close()
    exit(1)

# 5. Tentar inserção em lote
try:
    # Primeiro, vamos tentar limpar a tabela se já existia
    if tabela_existe:
        print("\n🧹 Limpando tabela existente...")
        cursor.execute("DELETE FROM escola")
        print(f"   {cursor.rowcount} registros removidos")
    
    # Inserir todos os dados
    print("\n📥 Inserindo dados na tabela...")
    
    # Inserção linha por linha para debug
    inseridos = 0
    for i, dado in enumerate(dados_para_inserir, 1):
        try:
            cursor.execute("""
                INSERT INTO escola (id, inep, escola, endereco, bairro, 
                                  distrito, gestor, telefone_extraido, localidade_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, dado)
            inseridos += 1
            
            # Mostrar progresso a cada 10 registros
            if i % 10 == 0:
                print(f"   Progresso: {i}/{len(dados_para_inserir)} registros")
                
        except psycopg2.IntegrityError as e:
            print(f"⚠️  Erro de integridade na linha {i} (ID: {dado[0]}): {e}")
            # Tentar UPDATE se INSERT falhar
            try:
                cursor.execute("""
                    UPDATE escola SET 
                        inep = %s,
                        escola = %s,
                        endereco = %s,
                        bairro = %s,
                        distrito = %s,
                        gestor = %s,
                        telefone_extraido = %s,
                        localidade_id = %s
                    WHERE id = %s
                """, (dado[1], dado[2], dado[3], dado[4], dado[5], 
                      dado[6], dado[7], dado[8], dado[0]))
                print(f"   ✅ Registro ID {dado[0]} atualizado")
                inseridos += 1
            except Exception as update_error:
                print(f"   ❌ Falha no UPDATE também: {update_error}")
                
        except Exception as e:
            print(f"❌ Erro na linha {i} (ID: {dado[0]}): {e}")
    
    # Fazer commit
    conn.commit()
    print(f"\n✅ Commit realizado! {inseridos} registros processados")
    
except Exception as e:
    print(f"❌ Erro durante a inserção: {e}")
    print(traceback.format_exc())
    conn.rollback()
    print("🔄 Rollback realizado")

# 6. Verificar resultado
print(f"\n🔍 Verificando resultado da inserção...")
try:
    cursor.execute("SELECT COUNT(*) FROM escola")
    total_depois = cursor.fetchone()[0]
    print(f"✅ Total de registros na tabela 'escola': {total_depois}")
    
    if total_depois > 0:
        print(f"\n📝 Amostra dos dados inseridos:")
        cursor.execute("SELECT id, escola, inep FROM escola ORDER BY id LIMIT 5")
        for registro in cursor.fetchall():
            print(f"   ID: {registro[0]}, Escola: {registro[1]}, INEP: {registro[2]}")
    else:
        print("❌ A tabela está vazia após a inserção!")
        
except Exception as e:
    print(f"❌ Erro ao verificar resultado: {e}")

# 7. Fechar conexão
cursor.close()
conn.close()
print("\n🔒 Conexão com o banco de dados encerrada.")