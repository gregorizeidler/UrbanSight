"""
Profile Chatbot Agent
Chatbot interativo para definir perfil do usuário
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from openai import OpenAI
import json

logger = logging.getLogger(__name__)

@dataclass
class UserProfile:
    # Dados demográficos
    age_group: str  # "18-25", "26-35", "36-45", "46-60", "60+"
    family_status: str  # "Solteiro", "Casal", "Família com crianças", "Família sem crianças"
    income_level: str  # "Baixa", "Média", "Média-alta", "Alta"
    
    # Estilo de vida
    work_style: str  # "Presencial", "Híbrido", "Remoto"
    transport_preference: str  # "Carro", "Transporte público", "Bicicleta", "Caminhada"
    social_lifestyle: str  # "Caseiro", "Social moderado", "Muito social"
    
    # Prioridades habitacionais
    property_type: str  # "Apartamento", "Casa", "Ambos"
    budget_range: str  # "Até 300k", "300k-500k", "500k-1M", "1M+"
    investment_purpose: str  # "Moradia", "Investimento", "Ambos"
    
    # Preferências urbanas
    priority_factors: List[str]  # Ex: ["Segurança", "Transporte", "Escolas", "Lazer"]
    neighborhood_style: str  # "Centro", "Residencial", "Misto", "Subúrbio"
    noise_tolerance: str  # "Baixa", "Média", "Alta"
    
    # Necessidades específicas
    has_pets: bool
    has_elderly: bool
    has_children: bool
    accessibility_needs: bool
    
    # Score de compatibilidade
    compatibility_weights: Dict[str, float]

@dataclass
class ChatbotQuestion:
    id: str
    question: str
    options: List[str]
    question_type: str  # "single", "multiple", "scale"
    category: str

@dataclass
class ProfileChatbotResult:
    user_profile: UserProfile
    compatibility_matrix: Dict[str, float]
    personalized_recommendations: List[str]
    profile_summary: str
    success: bool
    error_message: Optional[str] = None

class ProfileChatbot:
    """Chatbot interativo para definir perfil do usuário"""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        self.openai_client = OpenAI(api_key=openai_api_key) if openai_api_key else None
        self.questions = self._initialize_questions()
        
    def _initialize_questions(self) -> List[ChatbotQuestion]:
        """Inicializa as perguntas do chatbot"""
        return [
            ChatbotQuestion(
                id="age_group",
                question="👋 Qual sua faixa etária?",
                options=["18-25 anos", "26-35 anos", "36-45 anos", "46-60 anos", "60+ anos"],
                question_type="single",
                category="demográfico"
            ),
            ChatbotQuestion(
                id="family_status",
                question="👨‍👩‍👧‍👦 Qual sua situação familiar atual?",
                options=["Solteiro(a)", "Casal sem filhos", "Casal com filhos", "Pai/mãe solo", "Dividindo moradia"],
                question_type="single",
                category="demográfico"
            ),
            ChatbotQuestion(
                id="income_level",
                question="💰 Como você classificaria sua renda familiar?",
                options=["Até 5 salários mínimos", "5-10 salários mínimos", "10-20 salários mínimos", "Acima de 20 salários mínimos"],
                question_type="single",
                category="demográfico"
            ),
            ChatbotQuestion(
                id="work_style",
                question="💼 Como é seu estilo de trabalho?",
                options=["100% presencial", "Híbrido (casa + escritório)", "100% remoto", "Aposentado(a)", "Estudante"],
                question_type="single",
                category="estilo_vida"
            ),
            ChatbotQuestion(
                id="transport_preference",
                question="🚗 Qual seu meio de transporte preferido no dia a dia?",
                options=["Carro próprio", "Transporte público", "Bicicleta", "Caminhada", "Motocicleta", "Aplicativos de transporte"],
                question_type="multiple",
                category="estilo_vida"
            ),
            ChatbotQuestion(
                id="social_lifestyle",
                question="🎉 Como você descreveria seu estilo social?",
                options=["Prefiro ficar em casa", "Saídas ocasionais", "Vida social ativa", "Muito sociável - sempre saindo"],
                question_type="single",
                category="estilo_vida"
            ),
            ChatbotQuestion(
                id="property_type",
                question="🏠 Que tipo de imóvel você busca?",
                options=["Apartamento", "Casa", "Studio/Loft", "Não tenho preferência"],
                question_type="single",
                category="habitacional"
            ),
            ChatbotQuestion(
                id="investment_purpose",
                question="🎯 Qual o principal objetivo da compra?",
                options=["Para morar", "Para investimento/aluguel", "Ambos (morar e investir)", "Casa de veraneio"],
                question_type="single",
                category="habitacional"
            ),
            ChatbotQuestion(
                id="priority_factors",
                question="⭐ Quais fatores são mais importantes para você? (pode escolher até 4)",
                options=[
                    "Segurança", "Proximidade ao trabalho", "Transporte público", 
                    "Escolas/educação", "Hospitais/saúde", "Comércio/shopping", 
                    "Restaurantes", "Vida noturna", "Parques/lazer", "Academia/esportes",
                    "Silêncio/tranquilidade", "Preço acessível"
                ],
                question_type="multiple",
                category="preferências"
            ),
            ChatbotQuestion(
                id="neighborhood_style",
                question="🏙️ Que tipo de bairro você prefere?",
                options=["Centro da cidade", "Bairro residencial tranquilo", "Área mista (residencial + comercial)", "Subúrbio afastado"],
                question_type="single",
                category="preferências"
            ),
            ChatbotQuestion(
                id="noise_tolerance",
                question="🔊 Qual sua tolerância a ruído urbano?",
                options=["Preciso de muito silêncio", "Ruído moderado é ok", "Não me incomodo com ruído"],
                question_type="single",
                category="preferências"
            ),
            ChatbotQuestion(
                id="special_needs",
                question="🏠 Alguma necessidade especial? (pode marcar várias)",
                options=["Tenho pets", "Idosos na família", "Crianças pequenas", "Necessidades de acessibilidade", "Nenhuma"],
                question_type="multiple",
                category="necessidades"
            )
        ]
    
    def get_questions(self) -> List[ChatbotQuestion]:
        """Retorna todas as perguntas do chatbot"""
        return self.questions
    
    def process_responses(self, responses: Dict[str, Any]) -> ProfileChatbotResult:
        """Processa as respostas e cria o perfil do usuário"""
        
        try:
            logger.info("Processando respostas do chatbot de perfil")
            
            # Criar perfil baseado nas respostas
            user_profile = self._create_user_profile(responses)
            
            # Calcular matriz de compatibilidade
            compatibility_matrix = self._calculate_compatibility_weights(user_profile)
            
            # Gerar recomendações personalizadas
            recommendations = self._generate_personalized_recommendations(user_profile)
            
            # Criar resumo do perfil
            profile_summary = self._create_profile_summary(user_profile)
            
            return ProfileChatbotResult(
                user_profile=user_profile,
                compatibility_matrix=compatibility_matrix,
                personalized_recommendations=recommendations,
                profile_summary=profile_summary,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Erro processando respostas: {str(e)}")
            return ProfileChatbotResult(
                user_profile=None,
                compatibility_matrix={},
                personalized_recommendations=[],
                profile_summary="",
                success=False,
                error_message=str(e)
            )
    
    def _create_user_profile(self, responses: Dict[str, Any]) -> UserProfile:
        """Cria o perfil do usuário baseado nas respostas"""
        
        # Processar necessidades especiais
        special_needs = responses.get('special_needs', [])
        has_pets = "Tenho pets" in special_needs
        has_elderly = "Idosos na família" in special_needs
        has_children = "Crianças pequenas" in special_needs
        accessibility_needs = "Necessidades de acessibilidade" in special_needs
        
        # Calcular pesos de compatibilidade baseados nas prioridades
        priority_factors = responses.get('priority_factors', [])
        compatibility_weights = self._calculate_priority_weights(priority_factors)
        
        return UserProfile(
            age_group=responses.get('age_group', ''),
            family_status=responses.get('family_status', ''),
            income_level=responses.get('income_level', ''),
            work_style=responses.get('work_style', ''),
            transport_preference=', '.join(responses.get('transport_preference', [])),
            social_lifestyle=responses.get('social_lifestyle', ''),
            property_type=responses.get('property_type', ''),
            budget_range=self._income_to_budget(responses.get('income_level', '')),
            investment_purpose=responses.get('investment_purpose', ''),
            priority_factors=priority_factors,
            neighborhood_style=responses.get('neighborhood_style', ''),
            noise_tolerance=responses.get('noise_tolerance', ''),
            has_pets=has_pets,
            has_elderly=has_elderly,
            has_children=has_children,
            accessibility_needs=accessibility_needs,
            compatibility_weights=compatibility_weights
        )
    
    def _calculate_priority_weights(self, priority_factors: List[str]) -> Dict[str, float]:
        """Calcula pesos baseados nas prioridades do usuário"""
        
        weights = {
            'safety_score': 0.1,
            'accessibility_score': 0.15,
            'convenience_score': 0.15,
            'walk_score': 0.15,
            'quality_of_life_score': 0.15,
            'total_score': 0.3
        }
        
        # Ajustar pesos baseado nas prioridades
        priority_mapping = {
            'Segurança': 'safety_score',
            'Proximidade ao trabalho': 'accessibility_score',
            'Transporte público': 'accessibility_score',
            'Escolas/educação': 'quality_of_life_score',
            'Hospitais/saúde': 'quality_of_life_score',
            'Comércio/shopping': 'convenience_score',
            'Restaurantes': 'convenience_score',
            'Vida noturna': 'convenience_score',
            'Parques/lazer': 'walk_score',
            'Academia/esportes': 'walk_score',
            'Silêncio/tranquilidade': 'quality_of_life_score'
        }
        
        # Aumentar peso dos fatores prioritários
        for factor in priority_factors:
            if factor in priority_mapping:
                metric = priority_mapping[factor]
                weights[metric] += 0.05
                weights['total_score'] -= 0.01
        
        # Normalizar para somar 1.0
        total = sum(weights.values())
        return {k: v/total for k, v in weights.items()}
    
    def _income_to_budget(self, income_level: str) -> str:
        """Converte nível de renda em faixa de orçamento"""
        mapping = {
            "Até 5 salários mínimos": "Até R$ 400k",
            "5-10 salários mínimos": "R$ 400k - R$ 700k",
            "10-20 salários mínimos": "R$ 700k - R$ 1.5M",
            "Acima de 20 salários mínimos": "Acima de R$ 1.5M"
        }
        return mapping.get(income_level, "Não informado")
    
    def _calculate_compatibility_weights(self, profile: UserProfile) -> Dict[str, float]:
        """Calcula matriz de compatibilidade para diferentes tipos de análise"""
        
        base_weights = profile.compatibility_weights.copy()
        
        # Ajustar baseado no perfil específico
        if profile.has_children:
            base_weights['safety_score'] = min(0.4, base_weights['safety_score'] + 0.1)
            base_weights['quality_of_life_score'] = min(0.3, base_weights['quality_of_life_score'] + 0.05)
        
        if profile.has_elderly or profile.accessibility_needs:
            base_weights['accessibility_score'] = min(0.35, base_weights['accessibility_score'] + 0.1)
        
        if profile.work_style in ["100% presencial", "Híbrido (casa + escritório)"]:
            base_weights['accessibility_score'] = min(0.35, base_weights['accessibility_score'] + 0.05)
        
        if "Transporte público" in profile.transport_preference:
            base_weights['accessibility_score'] = min(0.35, base_weights['accessibility_score'] + 0.05)
        
        return base_weights
    
    def _generate_personalized_recommendations(self, profile: UserProfile) -> List[str]:
        """Gera recomendações personalizadas baseadas no perfil"""
        
        recommendations = []
        
        # Recomendações baseadas na família
        if profile.has_children:
            recommendations.append("🎓 Priorize áreas com boas escolas e parques infantis")
            recommendations.append("🚸 Busque ruas com menor tráfego e mais segurança")
        
        if profile.has_elderly:
            recommendations.append("🏥 Considere proximidade a hospitais e clínicas")
            recommendations.append("♿ Verifique acessibilidade de calçadas e transporte")
        
        if profile.has_pets:
            recommendations.append("🐕 Procure áreas com parques e espaços pet-friendly")
            recommendations.append("🏥 Verifique proximidade a veterinários")
        
        # Recomendações baseadas no trabalho
        if profile.work_style == "100% presencial":
            recommendations.append("🚊 Priorize acesso a transporte público ou proximidade ao trabalho")
        elif profile.work_style == "100% remoto":
            recommendations.append("🏠 Considere áreas mais tranquilas e com boa internet")
            recommendations.append("☕ Procure proximidade a cafés e coworkings")
        
        # Recomendações baseadas no estilo social
        if profile.social_lifestyle in ["Vida social ativa", "Muito sociável - sempre saindo"]:
            recommendations.append("🎉 Busque bairros com boa vida noturna e restaurantes")
            recommendations.append("🚇 Considere facilidade de transporte noturno")
        elif profile.social_lifestyle == "Prefiro ficar em casa":
            recommendations.append("🌳 Priorize áreas tranquilas e arborizadas")
            recommendations.append("📚 Considere proximidade a bibliotecas e espaços calmos")
        
        # Recomendações baseadas no orçamento
        if "Até R$ 400k" in profile.budget_range:
            recommendations.append("💰 Considere bairros em desenvolvimento para melhor custo-benefício")
            recommendations.append("🚊 Priorize transporte público para economizar com carro")
        
        # Recomendações baseadas no tipo de propriedade
        if profile.property_type == "Apartamento":
            recommendations.append("🏢 Verifique qualidade do condomínio e segurança do prédio")
        elif profile.property_type == "Casa":
            recommendations.append("🏡 Considere segurança do bairro e manutenção da propriedade")
        
        return recommendations
    
    def _create_profile_summary(self, profile: UserProfile) -> str:
        """Cria um resumo do perfil do usuário"""
        
        summary = f"""
        📋 RESUMO DO SEU PERFIL

        👤 Perfil Demográfico:
        • Idade: {profile.age_group}
        • Situação familiar: {profile.family_status}
        • Renda: {profile.income_level}

        💼 Estilo de Vida:
        • Trabalho: {profile.work_style}
        • Transporte: {profile.transport_preference}
        • Social: {profile.social_lifestyle}

        🏠 Preferências Habitacionais:
        • Tipo de imóvel: {profile.property_type}
        • Orçamento: {profile.budget_range}
        • Objetivo: {profile.investment_purpose}

        🎯 Suas Prioridades:
        {', '.join(profile.priority_factors)}

        🏙️ Estilo de Bairro: {profile.neighborhood_style}
        🔊 Tolerância a ruído: {profile.noise_tolerance}

        ✨ Necessidades Especiais:
        """
        
        special_needs = []
        if profile.has_pets:
            special_needs.append("Pet-friendly")
        if profile.has_children:
            special_needs.append("Adequado para crianças")
        if profile.has_elderly:
            special_needs.append("Adequado para idosos")
        if profile.accessibility_needs:
            special_needs.append("Acessibilidade")
        
        if special_needs:
            summary += f"• {', '.join(special_needs)}"
        else:
            summary += "• Nenhuma necessidade especial"
        
        return summary.strip()
    
    async def generate_ai_profile_analysis(self, profile: UserProfile) -> str:
        """Gera análise do perfil usando IA"""
        
        if not self.openai_client:
            return "Análise de IA indisponível. Configure a API key do OpenAI."
        
        try:
            prompt = f"""
            Você é um consultor imobiliário especializado em matching pessoa-propriedade. Analise este perfil:

            PERFIL DO CLIENTE:
            • Idade: {profile.age_group}
            • Família: {profile.family_status}
            • Trabalho: {profile.work_style}
            • Transporte: {profile.transport_preference}
            • Social: {profile.social_lifestyle}
            • Orçamento: {profile.budget_range}
            • Prioridades: {', '.join(profile.priority_factors)}
            • Bairro preferido: {profile.neighborhood_style}
            • Pets: {'Sim' if profile.has_pets else 'Não'}
            • Crianças: {'Sim' if profile.has_children else 'Não'}
            • Idosos: {'Sim' if profile.has_elderly else 'Não'}

            Forneça uma análise detalhada incluindo:
            1. Resumo psicográfico do cliente
            2. Tipo ideal de propriedade e localização
            3. Fatores críticos de decisão
            4. Possíveis pontos de flexibilidade
            5. Estratégia de busca recomendada

            Seja específico e personalizado. Responda em português brasileiro.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Você é um consultor imobiliário experiente especializado em análise de perfil de clientes."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1200,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Erro gerando análise de IA: {str(e)}")
            return f"Erro ao gerar análise de IA: {str(e)}" 